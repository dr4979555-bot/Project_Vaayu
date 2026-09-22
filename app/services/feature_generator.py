import pandas as pd


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


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create the exact 21 features required by the
    Random Forest temperature prediction model.
    """

    df = df.copy()

    # Make sure data is chronological
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    # -----------------------------
    # Time features
    # -----------------------------
    df["hour"] = df["time"].dt.hour
    df["day_of_week"] = df["time"].dt.dayofweek
    df["month"] = df["time"].dt.month

    # -----------------------------
    # Temperature lag features
    # -----------------------------
    df["temperature_lag_1"] = (
        df["temperature_2m"].shift(1)
    )

    df["temperature_lag_3"] = (
        df["temperature_2m"].shift(3)
    )

    df["temperature_lag_6"] = (
        df["temperature_2m"].shift(6)
    )

    df["temperature_lag_24"] = (
        df["temperature_2m"].shift(24)
    )

    # -----------------------------
    # Other weather lag features
    # -----------------------------
    df["humidity_lag_1"] = (
        df["relative_humidity_2m"].shift(1)
    )

    df["pressure_lag_1"] = (
        df["surface_pressure"].shift(1)
    )

    df["wind_speed_lag_1"] = (
        df["wind_speed_10m"].shift(1)
    )

    # -----------------------------
    # Rolling temperature features
    # -----------------------------
    df["temperature_rolling_3h"] = (
        df["temperature_2m"]
        .rolling(window=3)
        .mean()
    )

    df["temperature_rolling_6h"] = (
        df["temperature_2m"]
        .rolling(window=6)
        .mean()
    )

    df["temperature_rolling_24h"] = (
        df["temperature_2m"]
        .rolling(window=24)
        .mean()
    )

    # Remove rows where lag/rolling
    # features cannot be calculated
    df = df.dropna().reset_index(drop=True)

    return df


def get_model_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return only the 21 features required by the model.
    """

    missing_features = [
        feature for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    return df[FEATURES].copy()