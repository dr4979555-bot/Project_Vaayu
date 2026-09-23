const API_BASE = "https://project-vaayu.onrender.com";

const DEFAULT_LOCATION = {
    name: "Patna",
    latitude: 25.5941,
    longitude: 85.1376
};

const cityInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const locationBtn = document.getElementById("locationBtn");

let currentLocation = { ...DEFAULT_LOCATION };


/* =========================
   Utility Functions
========================= */

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}


function formatNumber(value, digits = 0) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "N/A";
    }

    return number.toFixed(digits);
}


function getFirstValue(object, keys, fallback = null) {
    for (const key of keys) {
        const parts = key.split(".");

        let value = object;

        for (const part of parts) {
            if (value == null) {
                break;
            }

            value = value[part];
        }

        if (
            value !== undefined &&
            value !== null &&
            value !== ""
        ) {
            return value;
        }
    }

    return fallback;
}


function conditionFromWeatherCode(code) {

    const weatherCode = Number(code);

    const conditions = {
        0: "Clear Sky",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing Rime Fog",
        51: "Light Drizzle",
        53: "Moderate Drizzle",
        55: "Dense Drizzle",
        56: "Freezing Drizzle",
        57: "Freezing Drizzle",
        61: "Light Rain",
        63: "Moderate Rain",
        65: "Heavy Rain",
        66: "Freezing Rain",
        67: "Freezing Rain",
        71: "Light Snow",
        73: "Moderate Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Rain Showers",
        81: "Rain Showers",
        82: "Heavy Rain Showers",
        85: "Snow Showers",
        86: "Snow Showers",
        95: "Thunderstorm",
        96: "Thunderstorm with Hail",
        99: "Thunderstorm with Hail"
    };

    return conditions[weatherCode] || "Unknown";
}


function weatherIconClass(condition, code = null) {

    const text =
        `${condition || ""}`.toLowerCase();

    const weatherCode = Number(code);

    if (
        Number.isFinite(weatherCode)
        && [95, 96, 99].includes(weatherCode)
    ) {
        return "fa-solid fa-cloud-bolt";
    }

    if (
        Number.isFinite(weatherCode)
        && (
            weatherCode >= 51 &&
            weatherCode <= 67
        )
    ) {
        return "fa-solid fa-cloud-rain";
    }

    if (
        Number.isFinite(weatherCode)
        && (
            weatherCode >= 80 &&
            weatherCode <= 82
        )
    ) {
        return "fa-solid fa-cloud-showers-heavy";
    }

    if (
        text.includes("rain")
        || text.includes("drizzle")
        || text.includes("shower")
    ) {
        return "fa-solid fa-cloud-rain";
    }

    if (
        text.includes("cloud")
        || text.includes("overcast")
        || text.includes("fog")
    ) {
        return "fa-solid fa-cloud-sun";
    }

    return "fa-solid fa-sun";
}


function compassDirection(degrees) {

    const value = Number(degrees);

    if (!Number.isFinite(value)) {
        return "N/A";
    }

    const directions = [
        "N",
        "NE",
        "E",
        "SE",
        "S",
        "SW",
        "W",
        "NW"
    ];

    const index =
        Math.round(value / 45) % 8;

    return directions[index];
}


function formatForecastDate(dateString) {

    if (!dateString) {
        return "N/A";
    }

    const date = new Date(
        `${dateString}T00:00:00`
    );

    if (Number.isNaN(date.getTime())) {
        return dateString;
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "numeric",
            month: "short"
        }
    );
}


function formatDayName(dateString, index) {

    if (index === 0) {
        return "Today";
    }

    if (!dateString) {
        return "--";
    }

    const date = new Date(
        `${dateString}T00:00:00`
    );

    if (Number.isNaN(date.getTime())) {
        return "--";
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            weekday: "short"
        }
    );
}


function formatTime(value) {

    if (!value) {
        return "N/A";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleTimeString(
        "en-IN",
        {
            hour: "numeric",
            minute: "2-digit"
        }
    );
}


function findNumericFieldByKeyword(data, keyword) {
    if (!data || typeof data !== "object") {
        return null;
    }

    const normalizedKeyword =
        keyword.toLowerCase();

    function searchObject(object) {

        for (const [key, value] of Object.entries(object)) {

            if (
                key.toLowerCase().includes(
                    normalizedKeyword
                )
                &&
                typeof value === "number"
                &&
                Number.isFinite(value)
            ) {
                return value;
            }

            if (
                value &&
                typeof value === "object"
            ) {
                const found =
                    searchObject(value);

                if (found !== null) {
                    return found;
                }
            }
        }

        return null;
    }

    return searchObject(data);
}


/* =========================
   Current Weather
========================= */

function renderCurrentWeather(data, locationName) {

    const temperature = getFirstValue(
        data,
        [
            "temperature_c",
            "temperature",
            "current_temperature",
            "current.temperature_2m",
            "weather.temperature"
        ]
    );

   let humidity = getFirstValue(
    data,
    [
        "relative_humidity_2m",
        "relative_humidity_percent",
        "relative_humidity",
        "humidity",
        "humidity_percent",
        "current.relative_humidity_2m"
    ]
);

if (humidity === null) {
    humidity =
        findNumericFieldByKeyword(
            data,
            "humidity"
        );
}

    const pressure = getFirstValue(
    data,
    [
        "surface_pressure",
        "surface_pressure_hpa",
        "pressure_hpa",
        "pressure",
        "current.surface_pressure"
    ]
);

    const wind = getFirstValue(
        data,
        [
            "wind_speed_kmh",
            "wind_speed",
            "wind_kmh",
            "current.wind_speed_10m"
        ]
    );

    const windDirection = getFirstValue(
        data,
        [
            "wind_direction_10m",
            "wind_direction",
            "current.wind_direction_10m"
        ]
    );

    const weatherCode = getFirstValue(
        data,
        [
            "weather_code",
            "weathercode",
            "current.weather_code"
        ]
    );

    let condition = getFirstValue(
        data,
        [
            "condition",
            "weather_condition",
            "description",
            "current.condition"
        ]
    );

    if (!condition) {
        condition =
            conditionFromWeatherCode(
                weatherCode
            );
    }

    const cityName =
        getFirstValue(
            data,
            [
                "location_name",
                "city",
                "location.name"
            ],
            locationName
        );

    document.getElementById(
        "cityName"
    ).textContent =
        cityName || "Unknown Location";

    document.getElementById(
        "temperature"
    ).textContent =
        temperature !== null
            ? `${formatNumber(temperature, 1)}°C`
            : "N/A";

    document.getElementById(
        "condition"
    ).textContent =
        condition || "N/A";

    const apparentTemperature = getFirstValue(
    data,
    [
        "apparent_temperature_c",
        "feels_like_c",
        "feels_like",
        "current.apparent_temperature"
    ]
);

document.getElementById(
    "feelsLike"
).textContent =
    apparentTemperature !== null
        ? `Feels like ${formatNumber(apparentTemperature, 1)}°C`
        : "Feels like data unavailable";

    document.getElementById(
        "humidity"
    ).textContent =
        humidity !== null
            ? `${formatNumber(humidity)}%`
            : "N/A";

    document.getElementById(
        "wind"
    ).textContent =
        wind !== null
            ? `${formatNumber(wind, 1)} km/h`
            : "N/A";

    document.getElementById(
        "pressure"
    ).textContent =
        pressure !== null
            ? `${formatNumber(pressure, 1)} hPa`
            : "N/A";

    const weatherIcon =
        document.querySelector(
            ".weather-main .weather-icon i"
        );

    if (weatherIcon) {

        weatherIcon.className =
            weatherIconClass(
                condition,
                weatherCode
            );
    }

    const topLocation =
        document.querySelector(
            ".topbar .location b"
        );

    if (topLocation) {

        topLocation.textContent =
            cityName || locationName;
    }

    const directionElement =
        document.getElementById(
            "windDirection"
        );

    if (directionElement) {

        directionElement.textContent =
            compassDirection(
                windDirection
            );
    }
}


/* =========================
   Forecast
========================= */

function renderForecast(data) {

    const container =
        document.querySelector(
            ".forecast-container"
        );

    if (!container) {
        return;
    }

    const forecastDays =
        data.forecast_days ||
        data.forecast ||
        [];

    if (!Array.isArray(forecastDays)
        || forecastDays.length === 0) {

        container.innerHTML =
            "<p>Forecast data unavailable.</p>";

        return;
    }

    container.innerHTML =
        forecastDays
            .slice(0, 7)
            .map((day, index) => {

                const condition =
                    day.condition ||
                    conditionFromWeatherCode(
                        day.weather_code
                    );

                const icon =
                    weatherIconClass(
                        condition,
                        day.weather_code
                    );

                const maxTemp =
                    getFirstValue(
                        day,
                        [
                            "temperature_max_c",
                            "temperature_max",
                            "max_temperature_c",
                            "max_temp"
                        ]
                    );

                const minTemp =
                    getFirstValue(
                        day,
                        [
                            "temperature_min_c",
                            "temperature_min",
                            "min_temperature_c",
                            "min_temp"
                        ]
                    );

                return `
                    <div
                        class="forecast-card ${index === 0 ? "active" : ""}"
                        data-day="${escapeHtml(
                            formatDayName(
                                day.date,
                                index
                            )
                        )}"
                    >

                        <h3>
                            ${escapeHtml(
                                formatDayName(
                                    day.date,
                                    index
                                )
                            )}
                        </h3>

                        <p>
                            ${escapeHtml(
                                formatForecastDate(
                                    day.date
                                )
                            )}
                        </p>

                        <i
                            class="${icon} weather-icon"
                        ></i>

                        <h2>
                            ${
                                maxTemp !== null
                                    ? `${formatNumber(
                                        maxTemp
                                    )}°`
                                    : "--"
                            }
                        </h2>

                        <span>
                            ${
                                minTemp !== null
                                    ? `${formatNumber(
                                        minTemp
                                    )}°`
                                    : "--"
                            }
                        </span>

                    </div>
                `;

            })
            .join("");

    attachForecastCardEvents();
}


function attachForecastCardEvents() {

    const cards =
        document.querySelectorAll(
            ".forecast-card"
        );

    cards.forEach(card => {

        card.addEventListener(
            "click",
            () => {

                cards.forEach(
                    item =>
                        item.classList.remove(
                            "active"
                        )
                );

                card.classList.add(
                    "active"
                );

                if (navigator.vibrate) {
                    navigator.vibrate(40);
                }
            }
        );
    });
}


/* =========================
   Weather Alerts
========================= */

async function loadWeatherAlerts(
    latitude,
    longitude,
    cityName
) {

    const badge =
        document.querySelector(
            ".alert-badge"
        );

    const title =
        document.querySelector(
            ".alert-body h4"
        );

    const location =
        document.querySelector(
            ".alert-location"
        );

    const time =
        document.querySelector(
            ".alert-body small"
        );

    const description =
        document.querySelector(
            ".alert-text"
        );

    const button =
        document.querySelector(
            ".alert-btn"
        );

    try {

        const response =
            await fetch(
                `${API_BASE}/api/v1/alerts/active` +
                `?latitude=${latitude}` +
                `&longitude=${longitude}` +
                `&radius_km=50`
            );

        if (!response.ok) {
            throw new Error(
                `Alert API returned ${response.status}`
            );
        }

        const alerts =
            await response.json();

        if (
            !Array.isArray(alerts)
            || alerts.length === 0
        ) {

            badge.textContent =
                "No Active Alerts";

            title.textContent =
                "No Active Weather Alerts";

            location.innerHTML =
                `<i class="fa-solid fa-location-dot"></i>
                 ${escapeHtml(cityName)}`;

            time.innerHTML =
                `<i class="fa-regular fa-clock"></i>
                 Live monitoring`;

            description.textContent =
                "No active CAP weather alerts were found within 50 km of this location.";

            button.textContent =
                "View Alerts";

            return;
        }

        const alert = alerts[0];

        const alertTitle =
            alert.title ||
            alert.headline ||
            alert.event ||
            "Weather Alert";

        const alertDescription =
            alert.description ||
            alert.instruction ||
            alert.headline ||
            "Official weather advisory available.";

        const onset =
            alert.onset ||
            alert.sent ||
            alert.effective;

        badge.textContent =
            `${alerts.length} Active Alert${
                alerts.length > 1 ? "s" : ""
            }`;

        title.textContent =
            alertTitle;

        location.innerHTML =
            `<i class="fa-solid fa-location-dot"></i>
             ${escapeHtml(
                 alert.area ||
                 alert.location ||
                 cityName
             )}`;

        time.innerHTML =
            `<i class="fa-regular fa-clock"></i>
             ${escapeHtml(
                 formatTime(onset)
             )}`;

        description.textContent =
            alertDescription;

        button.textContent =
            "View Advisory";

    } catch (error) {

        console.error(
            "Alert API error:",
            error
        );

        badge.textContent =
            "Alert Status Unavailable";

        title.textContent =
            "Weather Alerts";

        description.textContent =
            "Unable to retrieve official weather alerts right now.";

        location.innerHTML =
            `<i class="fa-solid fa-location-dot"></i>
             ${escapeHtml(cityName)}`;
    }
}


/* =========================
   Highlights
========================= */

function renderHighlights(
    forecastData,
    nowcastData
) {

    const forecastDays =
        forecastData.forecast_days ||
        forecastData.forecast ||
        [];

    const today =
        forecastDays[0];

    if (today) {

        const sunrise =
            getFirstValue(
                today,
                [
                    "sunrise",
                    "sunrise_time"
                ]
            );

        const sunset =
            getFirstValue(
                today,
                [
                    "sunset",
                    "sunset_time"
                ]
            );

        const sunriseElement =
            document.getElementById(
                "sunriseValue"
            );

        const sunsetElement =
            document.getElementById(
                "sunsetValue"
            );

        if (sunriseElement) {
            sunriseElement.textContent =
                formatTime(sunrise);
        }

        if (sunsetElement) {
            sunsetElement.textContent =
                formatTime(sunset);
        }
    }

    const windDirection =
        getFirstValue(
            nowcastData,
            [
                "wind_direction_10m",
                "wind_direction",
                "current.wind_direction_10m"
            ]
        );

    const directionElement =
        document.getElementById(
            "windDirection"
        );

    if (directionElement) {

        directionElement.textContent =
            compassDirection(
                windDirection
            );
    }

    const uvElement =
        document.getElementById(
            "uvValue"
        );

    if (uvElement) {
        uvElement.textContent = "N/A";
    }

    const uvStatus =
        document.getElementById(
            "uvStatus"
        );

    if (uvStatus) {
        uvStatus.textContent =
            "Data not available";
    }

    const aqiElement =
        document.getElementById(
            "aqiValue"
        );

    if (aqiElement) {
        aqiElement.textContent = "N/A";
    }

    const aqiStatus =
        document.getElementById(
            "aqiStatus"
        );

    if (aqiStatus) {
        aqiStatus.textContent =
            "Data not available";
    }

    const visibilityElement =
        document.getElementById(
            "visibilityValue"
        );

    if (visibilityElement) {
        visibilityElement.textContent =
            "N/A";
    }

    const visibilityStatus =
        document.getElementById(
            "visibilityStatus"
        );

    if (visibilityStatus) {
        visibilityStatus.textContent =
            "Data not available";
    }
}


/* =========================
   Open-Meteo Geocoding
========================= */

async function geocodeCity(city) {

    const url =
        "https://geocoding-api.open-meteo.com/v1/search" +
        `?name=${encodeURIComponent(city)}` +
        "&count=1" +
        "&language=en" +
        "&format=json";

    const response =
        await fetch(url);

    if (!response.ok) {
        throw new Error(
            "Geocoding request failed."
        );
    }

    const data =
        await response.json();

    if (
        !data.results ||
        data.results.length === 0
    ) {
        throw new Error(
            "City not found."
        );
    }

    const result =
        data.results[0];

    return {
        name: result.name,
        latitude: result.latitude,
        longitude: result.longitude,
        country: result.country,
        admin1: result.admin1
    };
}


/* =========================
   Main Weather Loader
========================= */

async function loadDashboard(
    location
) {

    currentLocation = {
        ...location
    };

    console.log(
        "Loading dashboard for:",
        currentLocation
    );

    try {

        const nowcastUrl =
            `${API_BASE}/api/v1/chat/nowcast` +
            `?latitude=${currentLocation.latitude}` +
            `&longitude=${currentLocation.longitude}`;

        const forecastUrl =
            `${API_BASE}/api/v1/chat/forecast` +
            `?latitude=${currentLocation.latitude}` +
            `&longitude=${currentLocation.longitude}`;

        console.log(
            "Nowcast API:",
            nowcastUrl
        );

        console.log(
            "Forecast API:",
            forecastUrl
        );

        const [
            nowcastResponse,
            forecastResponse
        ] = await Promise.all([
            fetch(nowcastUrl),
            fetch(forecastUrl)
        ]);

        if (!nowcastResponse.ok) {

            throw new Error(
                `Nowcast API returned ${nowcastResponse.status}`
            );
        }

        if (!forecastResponse.ok) {

            throw new Error(
                `Forecast API returned ${forecastResponse.status}`
            );
        }

        const [
            nowcastData,
            forecastData
        ] = await Promise.all([
            nowcastResponse.json(),
            forecastResponse.json()
        ]);

        console.log(
            "Nowcast response:",
            nowcastData
        );

        console.log(
            "Forecast response:",
            forecastData
        );

        renderCurrentWeather(
            nowcastData,
            currentLocation.name
        );

        renderForecast(
            forecastData
        );

        renderHighlights(
            forecastData,
            nowcastData
        );

        await loadWeatherAlerts(
            currentLocation.latitude,
            currentLocation.longitude,
            currentLocation.name
        );

        const status =
            document.getElementById(
                "dashboardStatus"
            );

        if (status) {
            status.textContent =
                "Live weather data";
        }

        console.log(
            "Dashboard loaded successfully."
        );

    } catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );

        const status =
            document.getElementById(
                "dashboardStatus"
            );

        if (status) {

            status.textContent =
                "Unable to load live weather data.";
        }

        alert(
            "Unable to load live weather data right now."
        );
    }
}


/* =========================
   Search
========================= */

async function searchCity() {

    const city =
        cityInput.value.trim();

    if (!city) {

        alert(
            "Please enter a city name."
        );

        return;
    }

    searchBtn.disabled = true;

    try {

        const location =
            await geocodeCity(city);

        await loadDashboard(
            location
        );

    } catch (error) {

        console.error(
            "City search error:",
            error
        );

        alert(
            error.message ||
            "Unable to find this city."
        );

    } finally {

        searchBtn.disabled = false;
    }
}


searchBtn.addEventListener(
    "click",
    searchCity
);


cityInput.addEventListener(
    "keypress",
    event => {

        if (event.key === "Enter") {
            searchCity();
        }
    }
);


/* =========================
   Current Location
========================= */

locationBtn.addEventListener(
    "click",
    () => {

        console.log(
            "Location button clicked"
        );

        if (!navigator.geolocation) {

            alert(
                "Geolocation is not supported by this browser."
            );

            return;
        }

        navigator.geolocation.getCurrentPosition(

            async position => {

                const latitude =
                    position.coords.latitude;

                const longitude =
                    position.coords.longitude;

                const location = {
                    name: "Current Location",
                    latitude,
                    longitude
                };

                await loadDashboard(
                    location
                );
            },

            error => {

                console.error(
                    "Geolocation error:",
                    error
                );

                alert(
                    "Location permission was denied or unavailable."
                );
            }
        );
    }
);


/* =========================
   Profile Dropdown
========================= */

const profileBtn =
    document.getElementById(
        "profileBtn"
    );

const profileMenu =
    document.getElementById(
        "profileMenu"
    );

if (profileBtn && profileMenu) {

    profileBtn.addEventListener(
        "click",
        event => {

            event.stopPropagation();

            profileMenu.classList.toggle(
                "active"
            );
        }
    );

    document.addEventListener(
        "click",
        event => {

            if (
                !profileMenu.contains(event.target)
                &&
                !profileBtn.contains(event.target)
            ) {

                profileMenu.classList.remove(
                    "active"
                );
            }
        }
    );
}


/* =========================
   Initial Load
========================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDashboard(
            DEFAULT_LOCATION
        );
    }
);
