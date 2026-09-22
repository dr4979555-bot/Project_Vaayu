from pathlib import Path

import joblib
import pandas as pd


# Backend project root
BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = BASE_DIR / "models" / "random_forest_temperature_model.joblib"


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


class TemperaturePredictionService:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"ML model not found: {MODEL_PATH}"
            )

        self.model = joblib.load(MODEL_PATH)

    def predict(self, weather_data: dict) -> float:
        """
        Predict next-hour temperature.
        """

        missing_features = [
            feature
            for feature in FEATURES
            if feature not in weather_data
        ]

        if missing_features:
            raise ValueError(
                f"Missing required features: {missing_features}"
            )

        input_data = pd.DataFrame(
            [[weather_data[feature] for feature in FEATURES]],
            columns=FEATURES,
        )

        prediction = self.model.predict(input_data)[0]

        return round(float(prediction), 2)


# Load model once when service starts.
prediction_service = TemperaturePredictionService()