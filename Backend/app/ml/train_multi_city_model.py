import os

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DATA_PATH = "data/multi_city_weather_ml_2021_2025.csv"
MODEL_DIR = "models"

MODEL_PATH = (
    f"{MODEL_DIR}/multi_city_random_forest_temperature_model.joblib"
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


def evaluate_model(name, model, X_test, y_test):
    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    print(f"\n{name}")
    print("-" * 45)
    print(f"MAE:  {mae:.4f} °C")
    print(f"RMSE: {rmse:.4f} °C")
    print(f"R²:   {r2:.4f}")

    return mae, rmse, r2


def main():

    print("Loading multi-city ML dataset...")

    df = pd.read_csv(DATA_PATH)

    df["time"] = pd.to_datetime(
        df["time"]
    )

    # --------------------------------------------------
    # Make sure each city is chronologically ordered
    # --------------------------------------------------

    df = (
        df.sort_values(
            ["location", "time"]
        )
        .reset_index(drop=True)
    )

    print("\n========== DATASET ==========")
    print(f"Total rows: {len(df):,}")
    print(f"Cities: {df['location'].nunique()}")

    print("\nRows by city:")
    print(
        df["location"]
        .value_counts()
        .sort_index()
    )

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

        split_index = int(
            len(city_df) * 0.80
        )

        train_parts.append(
            city_df.iloc[:split_index]
        )

        test_parts.append(
            city_df.iloc[split_index:]
        )

    train_df = pd.concat(
        train_parts,
        ignore_index=True,
    )

    test_df = pd.concat(
        test_parts,
        ignore_index=True,
    )

    print("\n========== DATA SPLIT ==========")
    print(f"Training rows: {len(train_df):,}")
    print(f"Testing rows:  {len(test_df):,}")

    print("\nTraining date range:")
    print(
        train_df["time"].min(),
        "to",
        train_df["time"].max(),
    )

    print("\nTesting date range:")
    print(
        test_df["time"].min(),
        "to",
        test_df["time"].max(),
    )

    # --------------------------------------------------
    # Input columns
    # --------------------------------------------------

    X_train = train_df[
        FEATURES + [LOCATION_FEATURE]
    ]

    y_train = train_df[TARGET]

    X_test = test_df[
        FEATURES + [LOCATION_FEATURE]
    ]

    y_test = test_df[TARGET]

    # --------------------------------------------------
    # Baseline
    #
    # "Next hour = current temperature"
    # --------------------------------------------------

    baseline_predictions = test_df[
        "temperature_2m"
    ]

    baseline_mae = mean_absolute_error(
        y_test,
        baseline_predictions,
    )

    baseline_rmse = np.sqrt(
        mean_squared_error(
            y_test,
            baseline_predictions,
        )
    )

    baseline_r2 = r2_score(
        y_test,
        baseline_predictions,
    )

    print("\n========== BASELINE ==========")
    print(f"MAE:  {baseline_mae:.4f} °C")
    print(f"RMSE: {baseline_rmse:.4f} °C")
    print(f"R²:   {baseline_r2:.4f}")

    # --------------------------------------------------
    # Preprocessing
    #
    # Weather features stay numeric.
    # Location is one-hot encoded.
    # --------------------------------------------------

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "location",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                [LOCATION_FEATURE],
            )
        ],
        remainder="passthrough",
    )

    # --------------------------------------------------
    # Linear Regression baseline model
    # --------------------------------------------------

    linear_model = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "model",
                LinearRegression(),
            ),
        ]
    )

    print(
        "\nTraining multi-city Linear Regression..."
    )

    linear_model.fit(
        X_train,
        y_train,
    )

    linear_results = evaluate_model(
        "Multi-city Linear Regression",
        linear_model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Random Forest
    # --------------------------------------------------

    random_forest = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=100,
                    max_depth=20,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    print(
        "\nTraining multi-city Random Forest..."
    )
    print(
        "100 trees, max_depth=20"
    )

    random_forest.fit(
        X_train,
        y_train,
    )

    rf_results = evaluate_model(
        "Multi-city Random Forest",
        random_forest,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Per-city evaluation
    # --------------------------------------------------

    print(
        "\n========== PER-CITY RANDOM FOREST =========="
    )

    city_results = []

    for city in sorted(
        test_df["location"].unique()
    ):

        city_test = test_df[
            test_df["location"] == city
        ]

        city_X = city_test[
            FEATURES + [LOCATION_FEATURE]
        ]

        city_y = city_test[TARGET]

        city_predictions = random_forest.predict(
            city_X
        )

        city_mae = mean_absolute_error(
            city_y,
            city_predictions,
        )

        city_rmse = np.sqrt(
            mean_squared_error(
                city_y,
                city_predictions,
            )
        )

        city_r2 = r2_score(
            city_y,
            city_predictions,
        )

        city_results.append(
            {
                "location": city,
                "MAE": city_mae,
                "RMSE": city_rmse,
                "R2": city_r2,
            }
        )

        print(
            f"{city:12s} | "
            f"MAE: {city_mae:.4f} | "
            f"RMSE: {city_rmse:.4f} | "
            f"R²: {city_r2:.4f}"
        )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )

    joblib.dump(
        random_forest,
        MODEL_PATH,
    )

    print(
        "\n========== MODEL SAVED =========="
    )

    print(
        f"Saved to: {MODEL_PATH}"
    )

    # --------------------------------------------------
    # Final comparison
    # --------------------------------------------------

    print(
        "\n========== FINAL COMPARISON =========="
    )

    print(
        f"Baseline          | "
        f"MAE: {baseline_mae:.4f} | "
        f"RMSE: {baseline_rmse:.4f} | "
        f"R²: {baseline_r2:.4f}"
    )

    print(
        f"Linear Regression | "
        f"MAE: {linear_results[0]:.4f} | "
        f"RMSE: {linear_results[1]:.4f} | "
        f"R²: {linear_results[2]:.4f}"
    )

    print(
        f"Random Forest     | "
        f"MAE: {rf_results[0]:.4f} | "
        f"RMSE: {rf_results[1]:.4f} | "
        f"R²: {rf_results[2]:.4f}"
    )


if __name__ == "__main__":
    main()