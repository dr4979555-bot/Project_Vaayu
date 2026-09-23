import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


DATA_PATH = "data/patna_weather_ml.csv"
MODEL_DIR = "models"


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


def evaluate_model(name, model, X_test, y_test):
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)

    print(f"\n{name}")
    print("-" * 40)
    print(f"MAE:  {mae:.4f} °C")
    print(f"RMSE: {rmse:.4f} °C")
    print(f"R²:   {r2:.4f}")

    return mae, rmse, r2


def main():

    print("Loading ML dataset...")

    df = pd.read_csv(DATA_PATH)
    df["time"] = pd.to_datetime(df["time"])

    # Make sure data is chronological
    df = df.sort_values("time").reset_index(drop=True)

    # --------------------------------------------------
    # Time-based train/test split
    # --------------------------------------------------

    split_index = int(len(df) * 0.80)

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]

    print("\n========== DATA SPLIT ==========")
    print(f"Training rows: {len(train_df):,}")
    print(f"Testing rows:  {len(test_df):,}")

    print(f"\nTraining period:")
    print(train_df["time"].min(), "to", train_df["time"].max())

    print(f"\nTesting period:")
    print(test_df["time"].min(), "to", test_df["time"].max())

    # --------------------------------------------------
    # Baseline
    # --------------------------------------------------

    baseline_predictions = test_df["temperature_2m"]

    baseline_mae = mean_absolute_error(
        y_test,
        baseline_predictions
    )

    baseline_rmse = np.sqrt(
        mean_squared_error(
            y_test,
            baseline_predictions
        )
    )

    baseline_r2 = r2_score(
        y_test,
        baseline_predictions
    )

    print("\n========== BASELINE ==========")
    print(f"MAE:  {baseline_mae:.4f} °C")
    print(f"RMSE: {baseline_rmse:.4f} °C")
    print(f"R²:   {baseline_r2:.4f}")

    # --------------------------------------------------
    # Linear Regression
    # --------------------------------------------------

    linear_model = LinearRegression()

    print("\nTraining Linear Regression...")
    linear_model.fit(X_train, y_train)

    linear_results = evaluate_model(
        "Linear Regression",
        linear_model,
        X_test,
        y_test
    )

    # --------------------------------------------------
    # Random Forest
    # --------------------------------------------------

    random_forest = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    print("\nTraining Random Forest...")
    random_forest.fit(X_train, y_train)

    rf_results = evaluate_model(
        "Random Forest",
        random_forest,
        X_test,
        y_test
    )

    # --------------------------------------------------
    # Save models
    # --------------------------------------------------

    joblib.dump(
        linear_model,
        f"{MODEL_DIR}/linear_temperature_model.joblib"
    )

    joblib.dump(
        random_forest,
        f"{MODEL_DIR}/random_forest_temperature_model.joblib"
    )

    print("\n========== MODELS SAVED ==========")
    print("models/linear_temperature_model.joblib")
    print("models/random_forest_temperature_model.joblib")

    # --------------------------------------------------
    # Final comparison
    # --------------------------------------------------

    print("\n========== MODEL COMPARISON ==========")

    print(
        f"Baseline          | MAE: {baseline_mae:.4f} | "
        f"RMSE: {baseline_rmse:.4f} | R²: {baseline_r2:.4f}"
    )

    print(
        f"Linear Regression | MAE: {linear_results[0]:.4f} | "
        f"RMSE: {linear_results[1]:.4f} | R²: {linear_results[2]:.4f}"
    )

    print(
        f"Random Forest     | MAE: {rf_results[0]:.4f} | "
        f"RMSE: {rf_results[1]:.4f} | R²: {rf_results[2]:.4f}"
    )


if __name__ == "__main__":
    main()