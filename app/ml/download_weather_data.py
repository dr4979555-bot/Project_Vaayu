import requests
import pandas as pd
from pathlib import Path


LATITUDE = 25.5941
LONGITUDE = 85.1376

START_DATE = "2021-01-01"
END_DATE = "2025-12-31"

URL = "https://archive-api.open-meteo.com/v1/archive"

PARAMS = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "weather_code",
    ]),
    "timezone": "Asia/Kolkata",
    "temperature_unit": "celsius",
    "wind_speed_unit": "kmh",
    "precipitation_unit": "mm",
}


def main():
    print("Downloading historical weather data...")
    print(f"Location: Patna, Bihar")
    print(f"Period: {START_DATE} to {END_DATE}")

    response = requests.get(URL, params=PARAMS, timeout=60)
    response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        raise RuntimeError("Hourly weather data not found in API response.")

    hourly = data["hourly"]

    df = pd.DataFrame(hourly)

    df["time"] = pd.to_datetime(df["time"])

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "patna_weather_2021_2025.csv"

    df.to_csv(output_file, index=False)

    print("\nDownload complete.")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Saved to: {output_file}")
    print("\nColumns:")
    print(df.columns.tolist())


if __name__ == "__main__":
    main()