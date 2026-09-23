import os

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DATA_PATH = "data/multi_city_weather_ml_2021_2025.csv"
MODEL_DIR = "models"

# Separate small deployment model
MODEL_PATH = (
    f"{MODEL_DIR}/multi_city_random_forest_temperature_deployment.joblib"
)

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
LOCATION_FEATURE = "location"


def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    print("\n========== DEPLOYMENT MODEL RESULTS ==========")
    print(f"MAE:  {mae:.4f} °C")
    print(f"RMSE: {rmse:.4f} °C")
    print(f"R²:   {r2:.4f}")

    return mae, rmse, r2


def main():

    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    df["time"] = pd.to_datetime(df["time"])

    df = (
        df.sort_values(["location", "time"])
        .reset_index(drop=True)
    )

    print(f"Total rows: {len(df):,}")
    print(f"Cities: {df['location'].nunique()}")

    # --------------------------------------------------
    # City-wise chronological 80/20 split
    # --------------------------------------------------

    train_parts = []
    test_parts = []

    for city in sorted(df["location"].unique()):

        city_df = (
            df[df["location"] == city]
            .sort_values("time")
            .reset_index(drop=True)
        )

        split_index = int(len(city_df) * 0.80)

        train_parts.append(city_df.iloc[:split_index])
        test_parts.append(city_df.iloc[split_index:])

    train_df = pd.concat(train_parts, ignore_index=True)
    test_df = pd.concat(test_parts, ignore_index=True)

    print(f"Training rows: {len(train_df):,}")
    print(f"Testing rows:  {len(test_df):,}")

    X_train = train_df[FEATURES + [LOCATION_FEATURE]]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES + [LOCATION_FEATURE]]
    y_test = test_df[TARGET]

    # --------------------------------------------------
    # Preprocessing
    # --------------------------------------------------

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "location",
                OneHotEncoder(handle_unknown="ignore"),
                [LOCATION_FEATURE],
            )
        ],
        remainder="passthrough",
    )

    # --------------------------------------------------
    # SMALL RANDOM FOREST FOR RENDER
    #
    # Much smaller than the original:
    # 20 trees instead of 100
    # max_depth=10 instead of 20
    # --------------------------------------------------

    model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=20,
                    max_depth=10,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )

    print("\nTraining SMALL deployment Random Forest...")
    print("20 trees, max_depth=10, n_jobs=1")

    model.fit(X_train, y_train)

    evaluate_model(
        model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
        compress=3,
    )

    print("\n========== MODEL SAVED ==========")
    print(f"Saved to: {MODEL_PATH}")

    # --------------------------------------------------
    # Show file size
    # --------------------------------------------------

    size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)

    print(f"Model size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()