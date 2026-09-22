import joblib

from app.services.weather_service import (
    get_hourly_weather,
    get_patna_weather,
)
from app.services.realtime_weather import RealtimeWeatherService
from app.services.feature_generator import (
    create_features,
    get_model_features,
)


MODEL_PATH = "models/random_forest_temperature_model.joblib"


def _predict_from_weather_data(
    weather_df,
    location_name: str,
):
    """
    Generate ML features from weather data and predict
    the next-hour temperature.
    """

    # 1. Generate the same features used during training
    features_df = create_features(weather_df)

    # 2. Select the 21 model features
    model_input = get_model_features(features_df)

    # 3. Load trained Random Forest
    model = joblib.load(MODEL_PATH)

    # 4. Use the latest valid feature row
    latest_features = model_input.tail(1)

    latest_weather = features_df.tail(1).iloc[0]

    # 5. Predict next-hour temperature
    prediction = model.predict(latest_features)[0]

    return {
        "location": location_name,
        "current_time": str(latest_weather["time"]),
        "current_temperature_c": round(
            float(latest_weather["temperature_2m"]),
            2,
        ),
        "predicted_temperature_c": round(
            float(prediction),
            2,
        ),
        "prediction_for": "next_hour",
        "model": "Random Forest",
    }


def predict_patna_next_hour_temperature():
    """
    Backward-compatible Patna-specific prediction.
    """

    weather_df = get_patna_weather()

    return _predict_from_weather_data(
        weather_df=weather_df,
        location_name="Patna",
    )


async def predict_location_next_hour_temperature(
    location: str,
):
    """
    Predict next-hour temperature for any resolvable location.

    Location name
        ↓
    Existing geocoding service
        ↓
    Latitude + longitude
        ↓
    Hourly weather data
        ↓
    Feature engineering
        ↓
    Random Forest prediction
    """

    # 1. Resolve location using existing backend geocoder
    resolved = await RealtimeWeatherService.geocode_location(
        location
    )

    if resolved is None:
        raise ValueError(
            f"Could not resolve location: {location}"
        )

    latitude, longitude, resolved_name = resolved

    # 2. Fetch the same type of hourly data used by the ML pipeline
    weather_df = get_hourly_weather(
        latitude=latitude,
        longitude=longitude,
        past_hours=48,
    )

    # 3. Run the ML pipeline
    return _predict_from_weather_data(
        weather_df=weather_df,
        location_name=resolved_name,
    )