import joblib

from app.services.feature_generator import (
    create_features,
    get_model_features,
)
from app.services.realtime_weather import RealtimeWeatherService
from app.services.weather_service import get_hourly_weather


MODEL_PATH = (
    "models/multi_city_random_forest_temperature_deployment.joblib"
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


# These are the locations represented in the training dataset.
TRAINED_LOCATIONS = {
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


def canonicalize_location(location: str) -> str:
    """
    Convert user location names/aliases into the city names
    used during multi-city model training.
    """

    clean = location.strip().lower()

    if clean not in TRAINED_LOCATIONS:
        raise ValueError(
            "Location is not covered by the current multi-city "
            "ML model. Supported locations: "
            + ", ".join(
                sorted(
                    set(
                        TRAINED_LOCATIONS.values()
                    )
                )
            )
        )

    return TRAINED_LOCATIONS[clean]


async def predict_multi_city_next_hour_temperature(
    location: str,
):
    """
    Predict next-hour temperature using the trained
    multi-city Random Forest model.
    """

    # 1. Convert aliases to the exact training label.
    model_location = canonicalize_location(location)

    # 2. Resolve coordinates using existing backend geocoder.
    resolved = await RealtimeWeatherService.geocode_location(
        model_location
    )

    if resolved is None:
        raise ValueError(
            f"Could not resolve location: {location}"
        )

    latitude, longitude, resolved_name = resolved

    # 3. Fetch enough hourly history for lag/rolling features.
    weather_df = get_hourly_weather(
        latitude=latitude,
        longitude=longitude,
        past_hours=48,
    )

    # 4. Generate the same 21 features used during training.
    features_df = create_features(weather_df)

    # 5. Select the 21 weather/time features.
    model_input = get_model_features(features_df)

    # 6. Add the categorical location feature used during training.
    model_input["location"] = model_location

    # 7. Ensure exact training column structure.
    model_input = model_input[
        FEATURES + ["location"]
    ]

    # 8. Load trained multi-city model.
    model = joblib.load(MODEL_PATH)

    # 9. Latest valid feature row predicts the next hour.
    latest_features = model_input.tail(1)

    latest_weather = features_df.tail(1).iloc[0]

    prediction = model.predict(
        latest_features
    )[0]

    return {
        "location": model_location,
        "resolved_location": resolved_name,
        "latitude": round(float(latitude), 4),
        "longitude": round(float(longitude), 4),
        "current_time": str(
            latest_weather["time"]
        ),
        "current_temperature_c": round(
            float(
                latest_weather["temperature_2m"]
            ),
            2,
        ),
        "predicted_temperature_c": round(
            float(prediction),
            2,
        ),
        "prediction_for": "next_hour",
        "model": (
            "Multi-city Random Forest"
        ),
    }
