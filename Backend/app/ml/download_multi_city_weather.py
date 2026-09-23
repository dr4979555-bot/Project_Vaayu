import time
from pathlib import Path

import pandas as pd
import requests


URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2021-01-01"
END_DATE = "2025-12-31"

CITIES = {
    "Patna": (25.5941, 85.1376),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Kolkata": (22.5726, 88.3639),
    "Chennai": (13.0827, 80.2707),
    "Bengaluru": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
}

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
]

OUTPUT_FILE = Path("data") / "multi_city_weather_2021_2025.csv"


def download_city_weather(
    city: str,
    latitude: float,
    longitude: float,
    max_retries: int = 5,
) -> pd.DataFrame:

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Asia/Kolkata",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    for attempt in range(1, max_retries + 1):

        print(
            f"\nDownloading: {city} "
            f"(attempt {attempt}/{max_retries})"
        )

        try:
            response = requests.get(
                URL,
                params=params,
                timeout=120,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")

                if retry_after is not None:
                    delay = int(retry_after)
                else:
                    delay = 10 * attempt

                print(
                    f"Rate limited (429). "
                    f"Retrying automatically..."
                )

                time.sleep(delay)
                continue

            response.raise_for_status()

            data = response.json()

            if "hourly" not in data:
                raise RuntimeError(
                    f"Hourly weather data not found for {city}."
                )

            df = pd.DataFrame(data["hourly"])

            df["time"] = pd.to_datetime(df["time"])
            df["location"] = city

            columns = [
                "location",
                "time",
                *HOURLY_VARIABLES,
            ]

            return df[columns]

        except requests.RequestException as e:

            if attempt == max_retries:
                raise

            delay = 10 * attempt

            print(
                f"Request failed: {e}"
            )

            time.sleep(delay)

    raise RuntimeError(
        f"Failed to download weather data for {city}."
    )


def load_existing_data():
    if not OUTPUT_FILE.exists():
        return pd.DataFrame()

    print(
        f"\nExisting dataset found: {OUTPUT_FILE}"
    )

    df = pd.read_csv(
        OUTPUT_FILE,
        parse_dates=["time"],
    )

    print(
        f"Existing rows: {len(df):,}"
    )

    return df


def save_dataset(df):
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    df = (
        df.sort_values(
            ["location", "time"]
        )
        .drop_duplicates(
            subset=["location", "time"]
        )
        .reset_index(drop=True)
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return df


def main():

    print(
        "========== RESUMABLE MULTI-CITY WEATHER DOWNLOAD =========="
    )

    existing_df = load_existing_data()

    if existing_df.empty:
        completed_cities = set()
    else:
        completed_cities = set(
            existing_df["location"].dropna().unique()
        )

    print(
        f"\nCompleted cities: "
        f"{sorted(completed_cities)}"
    )

    all_data = [existing_df] if not existing_df.empty else []

    for city, (latitude, longitude) in CITIES.items():

        if city in completed_cities:
            print(
                f"\nSkipping {city} "
                f"(already downloaded)"
            )
            continue

        try:

            city_df = download_city_weather(
                city=city,
                latitude=latitude,
                longitude=longitude,
            )

            print(
                f"Downloaded {len(city_df):,} rows "
                f"for {city}"
            )

            all_data.append(city_df)

            # Save immediately so progress is not lost.
            combined_df = pd.concat(
                all_data,
                ignore_index=True,
            )

            combined_df = save_dataset(
                combined_df
            )

            all_data = [combined_df]

            completed_cities.add(city)

            print(
                f"Saved progress. "
                f"Total rows: {len(combined_df):,}"
            )

        except Exception as e:

            print(
                f"\nFAILED: {city}"
            )
            print(f"Reason: {e}")

    if not all_data:
        raise RuntimeError(
            "No weather data available."
        )

    final_df = pd.concat(
        all_data,
        ignore_index=True,
    )

    final_df = save_dataset(final_df)

    print(
        "\n========== FINAL DATASET =========="
    )
    print(
        f"Total rows: {len(final_df):,}"
    )
    print(
        f"Total columns: {len(final_df.columns)}"
    )
    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print("\nRows by city:")
    print(
        final_df["location"]
        .value_counts()
        .sort_index()
    )


if __name__ == "__main__":
    main()