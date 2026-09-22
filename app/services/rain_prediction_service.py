import httpx

OPEN_METEO_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


async def get_rain_prediction(
    latitude: float,
    longitude: float,
):
    """
    Fetch current rain conditions and the next several hours
    of precipitation probability from Open-Meteo.
    """

    params = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),

        "current": ",".join([
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "rain",
        ]),

        "hourly": ",".join([
            "precipitation_probability",
            "precipitation",
            "rain",
        ]),

        "forecast_days": 1,
        "timezone": "auto",
        "precipitation_unit": "mm",
        "wind_speed_unit": "kmh",
    }

    async with httpx.AsyncClient(
        timeout=10.0
    ) as client:

        response = await client.get(
            OPEN_METEO_FORECAST_URL,
            params=params,
        )

        response.raise_for_status()

    data = response.json()

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    hourly_times = hourly.get("time", [])
    probabilities = hourly.get(
        "precipitation_probability",
        [],
    )
    precipitation = hourly.get(
        "precipitation",
        [],
    )
    rain = hourly.get(
        "rain",
        [],
    )

    if not hourly_times:
        raise ValueError(
            "Hourly rain forecast data not available."
        )

    # Current forecast hour
    current_time = current.get("time")
    start_index = 0
    if current_time:

    # Current API time may be 19:45 while hourly
    # forecast timestamps are 19:00, 20:00, etc.
     current_hour_key = str(current_time)[:13]

    for index, hourly_time in enumerate(hourly_times):
        if str(hourly_time).startswith(current_hour_key):
            start_index = index
            break

    # Take current + next 5 hours
    end_index = min(
        start_index + 6,
        len(hourly_times),
    )

    hourly_forecast = []

    for index in range(
        start_index,
        end_index,
    ):

        probability = (
            probabilities[index]
            if index < len(probabilities)
            else 0
        )

        precipitation_value = (
            precipitation[index]
            if index < len(precipitation)
            else 0.0
        )

        rain_value = (
            rain[index]
            if index < len(rain)
            else 0.0
        )

        hourly_forecast.append({
            "time": hourly_times[index],
            "precipitation_probability_pct": (
                int(probability)
                if probability is not None
                else 0
            ),
            "precipitation_mm": round(
                float(
                    precipitation_value or 0.0
                ),
                2,
            ),
            "rain_mm": round(
                float(
                    rain_value or 0.0
                ),
                2,
            ),
        })

    # Maximum probability in the available day
    daily_probability = max(
        (
            int(value)
            for value in probabilities
            if value is not None
        ),
        default=0,
    )

    # Total forecast precipitation
    total_precipitation = sum(
        float(value or 0.0)
        for value in precipitation
    )

    return {
        "latitude": round(
            float(latitude),
            4,
        ),
        "longitude": round(
            float(longitude),
            4,
        ),
        "current_time": current_time,
        "current_humidity_pct": (
            float(
                current["relative_humidity_2m"]
            )
            if current.get("relative_humidity_2m")
            is not None
            else None
        ),
        "current_wind_speed_kmh": (
            float(
                current["wind_speed_10m"]
            )
            if current.get("wind_speed_10m")
            is not None
            else None
        ),
        "current_precipitation_mm": round(
            float(
                current.get(
                    "precipitation",
                    0.0,
                )
                or 0.0
            ),
            2,
        ),
        "current_rain_mm": round(
            float(
                current.get(
                    "rain",
                    0.0,
                )
                or 0.0
            ),
            2,
        ),
        "maximum_rain_probability_pct": (
            daily_probability
        ),
        "total_forecast_precipitation_mm": round(
            total_precipitation,
            2,
        ),
        "hourly": hourly_forecast,
    }