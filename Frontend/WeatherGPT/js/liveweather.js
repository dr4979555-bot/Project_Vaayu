const API_BASE_URL = "https://project-vaayu.onrender.com";

const FALLBACK_LOCATION = {
    latitude: 25.5941,
    longitude: 85.1376,
    name: "Patna, Bihar"
};


function getWeatherIcon(condition) {

    const value = (condition || "").toLowerCase();

    if (value.includes("thunder")) {
        return "fa-cloud-bolt";
    }

    if (value.includes("rain") || value.includes("drizzle")) {
        return "fa-cloud-rain";
    }

    if (value.includes("snow")) {
        return "fa-snowflake";
    }

    if (value.includes("cloud")) {
        return "fa-cloud";
    }

    if (value.includes("clear") || value.includes("sun")) {
        return "fa-sun";
    }

    return "fa-cloud-sun";
}


function getBrowserLocation() {

    return new Promise((resolve) => {

        if (!navigator.geolocation) {
            resolve(FALLBACK_LOCATION);
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {

                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    name: "Current Location"
                });

            },

            () => {

                console.warn(
                    "Browser location unavailable. Using Patna fallback."
                );

                resolve(FALLBACK_LOCATION);
            },

            {
                enableHighAccuracy: false,
                timeout: 5000,
                maximumAge: 300000
            }
        );
    });
}


async function loadLiveWeather() {

    const temperatureElement =
        document.getElementById("currentTemperature");

    const conditionElement =
        document.getElementById("weatherCondition");

    const locationElement =
        document.getElementById("weatherLocation");

    const updatedElement =
        document.getElementById("weatherUpdated");

    const humidityElement =
        document.getElementById("humidity");

    const windElement =
        document.getElementById("wind");

    const pressureElement =
        document.getElementById("pressure");

    const visibilityElement =
        document.getElementById("visibility");

    const iconElement =
        document.getElementById("weatherIcon");


    try {

        const location = await getBrowserLocation();

        const url =
            `${API_BASE_URL}/api/v1/chat/nowcast` +
            `?latitude=${encodeURIComponent(location.latitude)}` +
            `&longitude=${encodeURIComponent(location.longitude)}`;


        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });


        const data = await response.json();


        if (!response.ok) {

            const errorMessage =
                data && data.detail
                    ? data.detail
                    : "Unable to fetch live weather.";

            throw new Error(errorMessage);
        }


        // Current temperature
        if (data.temperature_c !== null &&
            data.temperature_c !== undefined) {

            temperatureElement.textContent =
                `${Number(data.temperature_c).toFixed(1)}°C`;
        }


        // Weather condition
        conditionElement.textContent =
            data.weather_condition || "Weather data available";


        // Location
        locationElement.textContent =
            data.station_name ||
            location.name;


        // Timestamp
        if (data.timestamp) {

            const updatedTime =
                new Date(data.timestamp);

            updatedElement.textContent =
                `Updated ${updatedTime.toLocaleTimeString(
                    [],
                    {
                        hour: "2-digit",
                        minute: "2-digit"
                    }
                )}`;

        } else {

            updatedElement.textContent =
                "Updated just now";
        }


        // Humidity
        if (data.humidity_pct !== null &&
            data.humidity_pct !== undefined) {

            humidityElement.textContent =
                `${Math.round(data.humidity_pct)}%`;
        }


        // Wind
        if (data.wind_speed_kmh !== null &&
            data.wind_speed_kmh !== undefined) {

            windElement.textContent =
                `${Number(data.wind_speed_kmh).toFixed(1)} km/h`;
        }


        // Pressure
        if (data.surface_pressure_hpa !== null &&
            data.surface_pressure_hpa !== undefined) {

            pressureElement.textContent =
                `${Number(data.surface_pressure_hpa).toFixed(1)} hPa`;
        }


        // Backend does not currently provide visibility
        // in this endpoint.
        visibilityElement.textContent =
            "N/A";


        // Weather icon
        const icon =
            getWeatherIcon(data.weather_condition);

        iconElement.className =
            `fa-solid ${icon}`;


        // Live status badge
        const badge =
            document.querySelector(".status");

        if (badge) {

            badge.innerHTML =
                '<i class="fa-solid fa-circle"></i> Live';
        }

    }

    catch (error) {

        console.error(
            "Live weather API error:",
            error
        );

        temperatureElement.textContent =
            "--°C";

        conditionElement.textContent =
            "Unable to load";

        locationElement.textContent =
            "Weather service unavailable";

        updatedElement.textContent =
            "Try again later";

        humidityElement.textContent =
            "--%";

        windElement.textContent =
            "-- km/h";

        pressureElement.textContent =
            "-- hPa";

        visibilityElement.textContent =
            "--";
    }
}


// Initial load
loadLiveWeather();


// Refresh every 5 minutes
setInterval(
    loadLiveWeather,
    5 * 60 * 1000
);
