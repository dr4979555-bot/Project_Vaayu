import pandas as pd
import joblib


DATA_PATH = "data/patna_weather_ml.csv"
MODEL_PATH = "models/random_forest_temperature_model.joblib"

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


def main():
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)

    df["time"] = pd.to_datetime(df["time"])

    print("Loading trained model...")
    model = joblib.load(MODEL_PATH)

    # Take the last available record
    row = df.iloc[-1]

    X = pd.DataFrame(
        [[row[feature] for feature in FEATURES]],
        columns=FEATURES
    )

    prediction = model.predict(X)[0]

    actual = row["target_temperature"]

    print("\n========== TEMPERATURE PREDICTION ==========")
    print(f"Time:              {row['time']}")
    print(f"Current temperature: {row['temperature_2m']:.2f} °C")
    print(f"Actual next hour:    {actual:.2f} °C")
    print(f"Predicted next hour: {prediction:.2f} °C")

    error = abs(actual - prediction)

    print(f"Absolute error:      {error:.2f} °C")

    print("\nPrediction test completed successfully.")


if __name__ == "__main__":
    main()