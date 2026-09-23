const API_BASE_URL = "https://project-vaayu.onrender.com";

const PATNA_LOCATION = {
    latitude: 25.5941,
    longitude: 85.1376,
    name: "Patna, Bihar"
};


function weatherIcon(condition) {
    const value = String(condition || "").toLowerCase();

    if (value.includes("thunder")) {
        return "fa-cloud-bolt";
    }

    if (value.includes("rain") || value.includes("drizzle")) {
        return "fa-cloud-rain";
    }

    if (value.includes("cloud")) {
        return "fa-cloud";
    }

    if (value.includes("clear")) {
        return "fa-sun";
    }

    return "fa-cloud-sun";
}


function displayDate(dateString) {
    const date = new Date(dateString + "T00:00:00");

    return {
        weekday: date.toLocaleDateString("en-US", {
            weekday: "short"
        }),
        shortDate: date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric"
        })
    };
}


function renderForecastCards(forecasts) {

    const container =
        document.getElementById("forecastGrid");

    if (!container) {
        console.error("forecastGrid not found");
        return;
    }

    container.innerHTML = "";

    forecasts.forEach((item, index) => {

        const date = displayDate(item.date);

        const card =
            document.createElement("div");

        card.className =
            index === 0
                ? "day-card active"
                : "day-card";

        card.innerHTML = `
            <h3>${index === 0 ? "Today" : date.weekday}</h3>

            <p>${date.shortDate}</p>

            <i class="fa-solid ${weatherIcon(item.condition)}"></i>

            <h2>${Math.round(item.temperature_max_c)}°</h2>

            <span>${Math.round(item.temperature_min_c)}°</span>
        `;

        container.appendChild(card);
    });

    console.log(
        "Forecast cards rendered:",
        container.children.length
    );
}


function renderTemperatureChart(forecasts) {

    const svg =
        document.getElementById("temperatureChart");

    if (!svg) {
        console.error("temperatureChart not found");
        return;
    }

    svg.innerHTML = "";

    const temperatures =
        forecasts.map(
            item => Number(item.temperature_max_c)
        );

    if (temperatures.length === 0) {
        return;
    }

    const width = 600;
    const height = 220;
    const padding = 40;

    const min = Math.min(...temperatures);
    const max = Math.max(...temperatures);
    const range = Math.max(max - min, 1);

    const points = temperatures.map(
        (temperature, index) => {

            const x =
                padding +
                (
                    index /
                    Math.max(
                        temperatures.length - 1,
                        1
                    )
                ) *
                (width - padding * 2);

            const y =
                height -
                padding -
                (
                    (temperature - min) /
                    range
                ) *
                (height - padding * 2);

            return `${x},${y}`;
        }
    );

    svg.innerHTML = `
        <polyline
            fill="none"
            stroke="#2563eb"
            stroke-width="4"
            points="${points.join(" ")}">
        </polyline>
    `;

    temperatures.forEach((temperature, index) => {

        const x =
            padding +
            (
                index /
                Math.max(
                    temperatures.length - 1,
                    1
                )
            ) *
            (width - padding * 2);

        const y =
            height -
            padding -
            (
                (temperature - min) /
                range
            ) *
            (height - padding * 2);

        svg.innerHTML += `
            <circle
                cx="${x}"
                cy="${y}"
                r="5"
                fill="#2563eb">
            </circle>
        `;
    });
}


function renderRainProbability(forecasts) {

    if (!forecasts.length) {
        return;
    }

    const item =
        forecasts.length > 1
            ? forecasts[1]
            : forecasts[0];

    const probability =
        Number(
            item.precipitation_probability_pct
        ) || 0;

    const fill =
        document.getElementById(
            "rainProbabilityFill"
        );

    const text =
        document.getElementById(
            "rainProbabilityText"
        );

    if (fill) {
        fill.style.width =
            `${Math.max(
                0,
                Math.min(
                    probability,
                    100
                )
            )}%`;
    }

    if (text) {

        const date =
            displayDate(item.date);

        text.textContent =
            `${probability}% chance of rain on ${date.shortDate}`;
    }
}


function renderSunriseSunset(forecast) {

    if (!forecast) {
        return;
    }

    const sunrise =
        document.getElementById(
            "sunriseTime"
        );

    const sunset =
        document.getElementById(
            "sunsetTime"
        );

    if (sunrise) {
        sunrise.textContent =
            new Date(
                forecast.sunrise
            ).toLocaleTimeString(
                [],
                {
                    hour: "numeric",
                    minute: "2-digit"
                }
            );
    }

    if (sunset) {
        sunset.textContent =
            new Date(
                forecast.sunset
            ).toLocaleTimeString(
                [],
                {
                    hour: "numeric",
                    minute: "2-digit"
                }
            );
    }
}


async function loadForecastPage() {

    console.log("Starting forecast page...");

    const locationElement =
        document.getElementById(
            "forecastLocation"
        );

    try {

        const url =
            `${API_BASE_URL}/api/v1/chat/forecast` +
            `?latitude=${PATNA_LOCATION.latitude}` +
            `&longitude=${PATNA_LOCATION.longitude}`;

        console.log(
            "Forecast API:",
            url
        );

        const response =
            await fetch(url);

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        console.log(
            "Forecast API response:",
            data
        );

        const forecasts =
            data.forecast_days;

        if (
            !Array.isArray(forecasts) ||
            forecasts.length === 0
        ) {
            throw new Error(
                "No forecast days returned."
            );
        }

        // Location
        if (locationElement) {

            locationElement.innerHTML = `
                <i class="fa-solid fa-location-dot"></i>
                ${PATNA_LOCATION.name}
            `;
        }

        // Cards
        renderForecastCards(
            forecasts
        );

        // Chart
        renderTemperatureChart(
            forecasts
        );

        // Rain probability
        renderRainProbability(
            forecasts
        );

        // Sunrise / sunset
        renderSunriseSunset(
            forecasts[0]
        );

        console.log(
            "Forecast page loaded successfully."
        );

    } catch (error) {

        console.error(
            "Forecast page error:",
            error
        );

        const container =
            document.getElementById(
                "forecastGrid"
            );

        if (container) {

            container.innerHTML = `
                <div class="day-card active">
                    <h3>Unavailable</h3>
                    <p>Try again</p>
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <h2>--°</h2>
                    <span>--°</span>
                </div>
            `;
        }

        if (locationElement) {

            locationElement.innerHTML = `
                <i class="fa-solid fa-location-dot"></i>
                Forecast unavailable
            `;
        }
    }
}


document.addEventListener(
    "DOMContentLoaded",
    loadForecastPage
);
