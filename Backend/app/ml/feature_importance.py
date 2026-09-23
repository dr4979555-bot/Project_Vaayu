import pandas as pd
import matplotlib.pyplot as plt
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

    print("Loading model...")

    model = joblib.load(MODEL_PATH)

    importance = pd.Series(
        model.feature_importances_,
        index=FEATURES
    ).sort_values(ascending=False)

    print("\n========== FEATURE IMPORTANCE ==========")
    print(importance.round(4))

    plt.figure(figsize=(10, 7))

    importance.sort_values().plot(kind="barh")

    plt.title("Random Forest Feature Importance")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()