from functools import lru_cache
from pathlib import Path

import pandas as pd


DATA_PATH = Path(
    "data/multi_city_weather_2021_2025.csv"
)

SUPPORTED_CITIES = {
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


@lru_cache(maxsize=1)
def _load_weather_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Historical weather dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    df["time"] = pd.to_datetime(df["time"])

    return df


def _resolve_city(city: str) -> str:
    normalized = city.strip().lower()

    if normalized not in SUPPORTED_CITIES:
        raise ValueError(
            "Unsupported climate location. Supported cities: "
            + ", ".join(
                sorted(
                    set(
                        SUPPORTED_CITIES.values()
                    )
                )
            )
        )

    return SUPPORTED_CITIES[normalized]


def get_climate_summary(city: str = "Patna"):

    resolved_city = _resolve_city(city)

    df = _load_weather_data()

    city_df = (
        df[df["location"] == resolved_city]
        .copy()
        .sort_values("time")
    )

    if city_df.empty:
        raise ValueError(
            f"No historical weather data found for {resolved_city}."
        )

    # --------------------------------------------------
    # Daily aggregation
    # --------------------------------------------------

    city_df["date"] = city_df["time"].dt.date
    city_df["year"] = city_df["time"].dt.year
    city_df["month"] = city_df["time"].dt.month

    daily = (
        city_df
        .groupby("date")
        .agg(
            max_temperature_c=(
                "temperature_2m",
                "max",
            ),
            min_temperature_c=(
                "temperature_2m",
                "min",
            ),
            rainfall_mm=(
                "precipitation",
                "sum",
            ),
        )
        .reset_index()
    )

    daily["date"] = pd.to_datetime(
        daily["date"]
    )

    # --------------------------------------------------
    # Average summer high
    # April + May + June
    # --------------------------------------------------

    summer_daily = daily[
        daily["date"].dt.month.isin(
            [4, 5, 6]
        )
    ]

    avg_summer_high = (
        float(
            summer_daily[
                "max_temperature_c"
            ].mean()
        )
        if not summer_daily.empty
        else None
    )

    # --------------------------------------------------
    # Annual rainfall
    # --------------------------------------------------

    yearly_rainfall = (
        daily
        .groupby(
            daily["date"].dt.year
        )["rainfall_mm"]
        .sum()
    )

    average_annual_rainfall = (
        float(
            yearly_rainfall.mean()
        )
        if not yearly_rainfall.empty
        else None
    )

    # --------------------------------------------------
    # Hottest recorded day
    # --------------------------------------------------

    hottest_index = (
        daily["max_temperature_c"]
        .idxmax()
    )

    hottest_day = daily.loc[
        hottest_index
    ]

    # --------------------------------------------------
    # Days with temperature >= 40°C
    # We deliberately don't label these "heatwave days".
    # --------------------------------------------------

    days_40_plus = int(
        (
            daily[
                "max_temperature_c"
            ] >= 40.0
        ).sum()
    )

    # --------------------------------------------------
    # Monthly average temperature trend
    # --------------------------------------------------

    monthly_temperature = (
        city_df
        .groupby("month")[
            "temperature_2m"
        ]
        .mean()
    )

    monthly_trend = []

    for month in range(1, 13):

        if month in monthly_temperature.index:

            monthly_trend.append(
                {
                    "month": month,
                    "average_temperature_c": round(
                        float(
                            monthly_temperature.loc[
                                month
                            ]
                        ),
                        2,
                    ),
                }
            )

    # --------------------------------------------------
    # Data range
    # --------------------------------------------------

    start_date = city_df["time"].min()
    end_date = city_df["time"].max()

    return {
        "location": resolved_city,
        "data_start": start_date.strftime(
            "%Y-%m-%d"
        ),
        "data_end": end_date.strftime(
            "%Y-%m-%d"
        ),
        "average_summer_high_c": round(
            avg_summer_high,
            2,
        )
        if avg_summer_high is not None
        else None,
        "average_annual_rainfall_mm": round(
            average_annual_rainfall,
            2,
        )
        if average_annual_rainfall is not None
        else None,
        "hottest_day": {
            "date": hottest_day[
                "date"
            ].strftime("%Y-%m-%d"),
            "temperature_c": round(
                float(
                    hottest_day[
                        "max_temperature_c"
                    ]
                ),
                2,
            ),
        },
        "days_40_plus_c": days_40_plus,
        "monthly_temperature_trend": monthly_trend,
    }