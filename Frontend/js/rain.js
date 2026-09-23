const API_BASE_URL = "https://project-vaayu.onrender.com";

const FALLBACK_LOCATION = {
    latitude: 25.5941,
    longitude: 85.1376,
    name: "Patna, Bihar"
};


// ------------------------------------------------------------
// Browser location
// ------------------------------------------------------------
function getBrowserLocation() {

    return new Promise((resolve) => {

        if (!navigator.geolocation) {
            resolve(FALLBACK_LOCATION);
            return;
        }

        navigator.geolocation.getCurrentPosition(

            (position) => {

                resolve({
                    latitude:
                        position.coords.latitude,

                    longitude:
                        position.coords.longitude,

                    name: "Current Location"
                });

            },

            () => {

                console.warn(
                    "Browser location unavailable. Using Patna."
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


// ------------------------------------------------------------
// Format time
// ------------------------------------------------------------
function formatTime(timeString) {

    const date =
        new Date(timeString);

    return date.toLocaleTimeString(
        [],
        {
            hour: "numeric",
            minute: "2-digit"
        }
    );
}


// ------------------------------------------------------------
// Create hourly rain box
// ------------------------------------------------------------
function createHourBox(
    forecast,
    index
) {

    const box =
        document.createElement("div");

    box.className =
        index === 0
            ? "hour-box active"
            : "hour-box";

    const timeLabel =
        index === 0
            ? "Now"
            : formatTime(
                forecast.time
            );

    box.innerHTML = `
        <p>${timeLabel}</p>

        <strong>
            ${forecast.precipitation_probability_pct}%
        </strong>
    `;

    return box;
}


// ------------------------------------------------------------
// Render hourly forecast
// ------------------------------------------------------------
function renderHourlyRain(
    hourly
) {

    const hourGrid =
        document.getElementById(
            "hourGrid"
        );

    if (!hourGrid) {
        return;
    }

    hourGrid.innerHTML = "";

    hourly.forEach(
        (forecast, index) => {

            const box =
                createHourBox(
                    forecast,
                    index
                );

            hourGrid.appendChild(
                box
            );
        }
    );
}


// ------------------------------------------------------------
// Load rain prediction
// ------------------------------------------------------------
async function loadRainPrediction() {

    try {

        const location =
            await getBrowserLocation();


        const url =
            `${API_BASE_URL}/api/v1/chat/rain-prediction` +
            `?latitude=${encodeURIComponent(
                location.latitude
            )}` +
            `&longitude=${encodeURIComponent(
                location.longitude
            )}`;


        console.log(
            "Rain prediction API:",
            url
        );


        const response =
            await fetch(
                url,
                {
                    method: "GET",
                    headers: {
                        "Accept":
                            "application/json"
                    }
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to fetch rain prediction."
            );
        }


        console.log(
            "Rain prediction response:",
            data
        );


        // ----------------------------------------------------
        // Location
        // ----------------------------------------------------

        const locationElement =
            document.getElementById(
                "rainLocation"
            );

        if (locationElement) {

            locationElement.innerHTML = `
                <i class="fa-solid fa-location-dot"></i>
                ${location.name}
            `;
        }


        // ----------------------------------------------------
        // Today's probability
        // ----------------------------------------------------

        const probability =
            Number(
                data.maximum_rain_probability_pct
            ) || 0;


        const probabilityElement =
            document.getElementById(
                "rainProbability"
            );

        if (probabilityElement) {

            probabilityElement.textContent =
                `${probability}%`;
        }


        // ----------------------------------------------------
        // Expected rainfall
        // ----------------------------------------------------

        const rainfall =
            Number(
                data.total_forecast_precipitation_mm
            ) || 0;


        const expectedRainfall =
            document.getElementById(
                "expectedRainfall"
            );

        const rainfallAmount =
            document.getElementById(
                "rainfallAmount"
            );


        if (expectedRainfall) {

            expectedRainfall.textContent =
                `Expected rainfall: ${rainfall.toFixed(1)} mm`;
        }


        if (rainfallAmount) {

            rainfallAmount.textContent =
                `${rainfall.toFixed(1)} mm`;
        }


        // ----------------------------------------------------
        // Humidity
        // ----------------------------------------------------

        const humidity =
            document.getElementById(
                "humidity"
            );

        if (humidity) {

            const value =
                Number(
                    data.current_humidity_pct
                );

            humidity.textContent =
                Number.isFinite(value)
                    ? `${Math.round(value)}%`
                    : "--%";
        }


        // ----------------------------------------------------
        // Wind
        // ----------------------------------------------------

        const windSpeed =
            document.getElementById(
                "windSpeed"
            );

        if (windSpeed) {

            const value =
                Number(
                    data.current_wind_speed_kmh
                );

            windSpeed.textContent =
                Number.isFinite(value)
                    ? `${value.toFixed(1)} km/h`
                    : "-- km/h";
        }


        // ----------------------------------------------------
        // Current time
        // ----------------------------------------------------

        const currentTime =
            document.getElementById(
                "currentTime"
            );

        if (
            currentTime &&
            data.current_time
        ) {

            currentTime.textContent =
                formatTime(
                    data.current_time
                );
        }


        // ----------------------------------------------------
        // Weather icon
        // ----------------------------------------------------

        const rainIcon =
            document.getElementById(
                "rainIcon"
            );

        if (rainIcon) {

            if (probability >= 70) {

                rainIcon.className =
                    "fa-solid fa-cloud-showers-heavy";

            } else if (probability >= 40) {

                rainIcon.className =
                    "fa-solid fa-cloud-rain";

            } else if (probability > 0) {

                rainIcon.className =
                    "fa-solid fa-cloud-sun";

            } else {

                rainIcon.className =
                    "fa-solid fa-sun";
            }
        }


        // ----------------------------------------------------
        // Hourly forecast
        // ----------------------------------------------------

        renderHourlyRain(
            data.hourly || []
        );


        console.log(
            "Rain prediction page loaded successfully."
        );

    }

    catch (error) {

        console.error(
            "Rain prediction API error:",
            error
        );


        const probability =
            document.getElementById(
                "rainProbability"
            );

        if (probability) {
            probability.textContent =
                "--%";
        }


        const expectedRainfall =
            document.getElementById(
                "expectedRainfall"
            );

        if (expectedRainfall) {
            expectedRainfall.textContent =
                "Rain forecast unavailable";
        }


        const hourGrid =
            document.getElementById(
                "hourGrid"
            );

        if (hourGrid) {

            hourGrid.innerHTML = `
                <div class="hour-box active">
                    <p>Unavailable</p>
                    <strong>--%</strong>
                </div>
            `;
        }
    }
}


// ------------------------------------------------------------
// Start
// ------------------------------------------------------------
document.addEventListener(
    "DOMContentLoaded",
    loadRainPrediction
);
