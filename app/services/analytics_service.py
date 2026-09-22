from functools import lru_cache
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = BASE_DIR / "data" / "multi_city_weather_2021_2025.csv"


SUPPORTED_LOCATIONS = {
    "patna": "Patna",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "mumbai": "Mumbai",
    "kolkata": "Kolkata",
    "chennai": "Chennai",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "hyderabad": "Hyderabad",
    "ahmedabad": "Ahmedabad",
}


def canonicalize_location(location: str) -> str:
    key = location.strip().lower()

    if key not in SUPPORTED_LOCATIONS:
        supported = ", ".join(sorted(set(SUPPORTED_LOCATIONS.values())))
        raise ValueError(
            f"Unsupported location '{location}'. "
            f"Supported locations: {supported}"
        )

    return SUPPORTED_LOCATIONS[key]


@lru_cache(maxsize=1)
def load_weather_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Weather dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = {
        "time",
        "location",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing)}"
        )

    df["time"] = pd.to_datetime(
        df["time"],
        errors="coerce"
    )

    numeric_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.dropna(
        subset=[
            "time",
            "location",
            "temperature_2m",
        ]
    ).copy()

    return df


def get_monthly_analytics(
    city: str = "Patna",
    year: int | None = None,
    month: int | None = None,
) -> dict:
    location = canonicalize_location(city)

    df = load_weather_data()

    city_df = df[
        df["location"].astype(str).str.lower()
        == location.lower()
    ].copy()

    if city_df.empty:
        raise ValueError(
            f"No weather data available for {location}."
        )

    city_df = city_df.sort_values("time")

    # ----------------------------------------
    # Default to latest available year/month
    # ----------------------------------------

    latest_timestamp = city_df["time"].max()

    if year is None:
        year = int(latest_timestamp.year)

    if month is None:
        month = int(latest_timestamp.month)

    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12.")

    # ----------------------------------------
    # Selected month
    # ----------------------------------------

    month_df = city_df[
        (city_df["time"].dt.year == year)
        & (city_df["time"].dt.month == month)
    ].copy()

    if month_df.empty:
        raise ValueError(
            f"No data available for {location} "
            f"for {year}-{month:02d}."
        )

    # ----------------------------------------
    # Daily aggregation
    # ----------------------------------------

    daily = (
        month_df
        .set_index("time")
        .resample("D")
        .agg(
            temperature_avg=("temperature_2m", "mean"),
            temperature_max=("temperature_2m", "max"),
            temperature_min=("temperature_2m", "min"),
            rainfall_mm=("precipitation", "sum"),
            humidity_avg=("relative_humidity_2m", "mean"),
            wind_avg=("wind_speed_10m", "mean"),
        )
        .dropna(subset=["temperature_avg"])
    )

    # ----------------------------------------
    # Temperature extremes
    # ----------------------------------------

    highest_temperature = float(
        month_df["temperature_2m"].max()
    )

    lowest_temperature = float(
        month_df["temperature_2m"].min()
    )

    highest_row = month_df.loc[
        month_df["temperature_2m"].idxmax()
    ]

    lowest_row = month_df.loc[
        month_df["temperature_2m"].idxmin()
    ]

    highest_timestamp = (
        highest_row["time"].isoformat()
        if pd.notna(highest_row["time"])
        else None
    )

    lowest_timestamp = (
        lowest_row["time"].isoformat()
        if pd.notna(lowest_row["time"])
        else None
    )

    # ----------------------------------------
    # Rainfall
    # ----------------------------------------

    total_rainfall = float(
        month_df["precipitation"]
        .fillna(0)
        .sum()
    )

    # ----------------------------------------
    # Humidity and wind
    # ----------------------------------------

    avg_humidity = float(
        month_df["relative_humidity_2m"]
        .mean()
    )

    avg_wind = float(
        month_df["wind_speed_10m"]
        .mean()
    )

    # ----------------------------------------
    # Dry / rainy days
    # ----------------------------------------

    dry_days = int(
        (daily["rainfall_mm"] <= 0.1).sum()
    )

    rainy_days = int(
        (daily["rainfall_mm"] > 0.1).sum()
    )

    # ----------------------------------------
    # Daily temperature trend
    # ----------------------------------------

    temperature_trend = []

    for timestamp, row in daily.iterrows():
        temperature_trend.append(
            {
                "date": timestamp.strftime("%Y-%m-%d"),
                "day": int(timestamp.day),
                "temperature_c": round(
                    float(row["temperature_avg"]),
                    2
                ),
            }
        )

    # ----------------------------------------
    # Monthly rainfall trend for selected year
    # ----------------------------------------

    year_df = city_df[
        city_df["time"].dt.year == year
    ].copy()

    monthly_rainfall = (
        year_df
        .groupby(
            year_df["time"].dt.month
        )["precipitation"]
        .sum()
    )

    rainfall_trend = []

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    for month_number in range(1, 13):
        rainfall_value = float(
            monthly_rainfall.get(month_number, 0.0)
        )

        rainfall_trend.append(
            {
                "month": month_names[month_number - 1],
                "month_number": month_number,
                "rainfall_mm": round(
                    rainfall_value,
                    2
                ),
            }
        )

    # ----------------------------------------
    # Data range
    # ----------------------------------------

    data_start = city_df["time"].min()
    data_end = city_df["time"].max()

    return {
        "status": "success",
        "location": location,
        "year": year,
        "month": month,
        "month_name": month_names[month - 1],
        "data_start": data_start.strftime("%Y-%m-%d"),
        "data_end": data_end.strftime("%Y-%m-%d"),

        "highest_temperature_c": round(
            highest_temperature,
            2
        ),

        "lowest_temperature_c": round(
            lowest_temperature,
            2
        ),

        "highest_temperature_time": highest_timestamp,

        "lowest_temperature_time": lowest_timestamp,

        "total_rainfall_mm": round(
            total_rainfall,
            2
        ),

        "average_humidity_percent": round(
            avg_humidity,
            2
        ),

        "average_wind_speed_kmh": round(
            avg_wind,
            2
        ),

        "dry_days": dry_days,

        "rainy_days": rainy_days,

        "temperature_trend": temperature_trend,

        "monthly_rainfall": rainfall_trend,
    }