import pandas as pd


DATA_PATH = "data/patna_weather_2021_2025.csv"
OUTPUT_PATH = "data/patna_weather_ml.csv"


def main():
    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)
    df["time"] = pd.to_datetime(df["time"])

    # Make sure data is chronologically ordered
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
    df["temperature_lag_1"] = df["temperature_2m"].shift(1)
    df["temperature_lag_3"] = df["temperature_2m"].shift(3)
    df["temperature_lag_6"] = df["temperature_2m"].shift(6)
    df["temperature_lag_24"] = df["temperature_2m"].shift(24)

    # -----------------------------
    # Other weather lag features
    # -----------------------------
    df["humidity_lag_1"] = df["relative_humidity_2m"].shift(1)
    df["pressure_lag_1"] = df["surface_pressure"].shift(1)
    df["wind_speed_lag_1"] = df["wind_speed_10m"].shift(1)

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

    # -----------------------------
    # Prediction target
    # -----------------------------
    df["target_temperature"] = df["temperature_2m"].shift(-1)

    # Remove rows created by lag/target operations
    df = df.dropna().reset_index(drop=True)

    # Save ML-ready dataset
    df.to_csv(OUTPUT_PATH, index=False)

    print("\n========== FEATURE ENGINEERING COMPLETE ==========")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nFeatures:")
    print(df.columns.tolist())

    print("\nSample:")
    print(df.head())


if __name__ == "__main__":
    main()