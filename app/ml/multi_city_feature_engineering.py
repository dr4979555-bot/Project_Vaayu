import pandas as pd


DATA_PATH = "data/multi_city_weather_2021_2025.csv"
OUTPUT_PATH = "data/multi_city_weather_ml_2021_2025.csv"


FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
    "hour",
    "day_of_week",
    "month",
    "temperature_lag_1",
    "temperature_lag_3",
    "temperature_lag_6",
    "temperature_lag_24",
    "humidity_lag_1",
    "pressure_lag_1",
    "wind_speed_lag_1",
    "temperature_rolling_3h",
    "temperature_rolling_6h",
    "temperature_rolling_24h",
]

TARGET = "target_temperature"


def main():

    print("Loading multi-city weather dataset...")

    df = pd.read_csv(DATA_PATH)
    df["time"] = pd.to_datetime(df["time"])

    # --------------------------------------------------
    # Important:
    # Sort separately by location and time.
    # This prevents one city's history from becoming
    # another city's lag/rolling history.
    # --------------------------------------------------

    df = (
        df.sort_values(["location", "time"])
        .reset_index(drop=True)
    )

    # --------------------------------------------------
    # Time features
    # --------------------------------------------------

    df["hour"] = df["time"].dt.hour
    df["day_of_week"] = df["time"].dt.dayofweek
    df["month"] = df["time"].dt.month

    # --------------------------------------------------
    # Temperature lag features
    # Calculated separately for every city.
    # --------------------------------------------------

    grouped_temperature = (
        df.groupby("location")["temperature_2m"]
    )

    df["temperature_lag_1"] = (
        grouped_temperature.shift(1)
    )

    df["temperature_lag_3"] = (
        grouped_temperature.shift(3)
    )

    df["temperature_lag_6"] = (
        grouped_temperature.shift(6)
    )

    df["temperature_lag_24"] = (
        grouped_temperature.shift(24)
    )

    # --------------------------------------------------
    # Other weather lag features
    # --------------------------------------------------

    df["humidity_lag_1"] = (
        df.groupby("location")["relative_humidity_2m"]
        .shift(1)
    )

    df["pressure_lag_1"] = (
        df.groupby("location")["surface_pressure"]
        .shift(1)
    )

    df["wind_speed_lag_1"] = (
        df.groupby("location")["wind_speed_10m"]
        .shift(1)
    )

    # --------------------------------------------------
    # Rolling temperature features
    # Calculated independently for each city.
    # --------------------------------------------------

    df["temperature_rolling_3h"] = (
        df.groupby("location")["temperature_2m"]
        .transform(
            lambda s: s.rolling(window=3).mean()
        )
    )

    df["temperature_rolling_6h"] = (
        df.groupby("location")["temperature_2m"]
        .transform(
            lambda s: s.rolling(window=6).mean()
        )
    )

    df["temperature_rolling_24h"] = (
        df.groupby("location")["temperature_2m"]
        .transform(
            lambda s: s.rolling(window=24).mean()
        )
    )

    # --------------------------------------------------
    # Next-hour prediction target
    # Also calculated separately for every city.
    # --------------------------------------------------

    df[TARGET] = (
        df.groupby("location")["temperature_2m"]
        .shift(-1)
    )

    # --------------------------------------------------
    # Remove rows where lag/rolling/target is unavailable
    # --------------------------------------------------

    df = (
        df.dropna(
            subset=FEATURES + [TARGET]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------
    # Save ML-ready dataset
    # --------------------------------------------------

    df.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        "\n========== MULTI-CITY FEATURE ENGINEERING COMPLETE =========="
    )

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nRows by city:")
    print(
        df["location"]
        .value_counts()
        .sort_index()
    )

    print("\nML features:")
    print(FEATURES)

    print("\nSample:")
    print(
        df[
            ["location", "time"]
            + FEATURES
            + [TARGET]
        ].head()
    )


if __name__ == "__main__":
    main()