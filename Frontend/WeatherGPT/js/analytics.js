console.log("Analytics page starting...");

const API_BASE = "https://project-vaayu.onrender.com";

const CITY = "Patna";
const YEAR = 2025;
const MONTH = 9;

function formatNumber(value, digits = 0) {
    const number = Number(value);

    if (Number.isNaN(number)) {
        return "N/A";
    }

    return number.toFixed(digits);
}


function formatDateTime(value) {
    if (!value) {
        return "N/A";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    });
}


function renderTemperatureChart(data) {

    const svg = document.getElementById("temperatureChart");

    if (!svg) {
        return;
    }

    const trend = data.temperature_trend || [];

    if (trend.length === 0) {
        svg.innerHTML = "";
        return;
    }

    const width = 700;
    const height = 260;

    const left = 40;
    const right = 660;

    const top = 30;
    const bottom = 220;

    const temperatures = trend.map(
        item => Number(item.temperature_c)
    );

    const minTemp = Math.min(...temperatures);
    const maxTemp = Math.max(...temperatures);

    const range =
        maxTemp - minTemp === 0
            ? 1
            : maxTemp - minTemp;

    const points = trend.map((item, index) => {

        const x =
            trend.length === 1
                ? width / 2
                : left +
                  (
                      index /
                      (trend.length - 1)
                  ) *
                  (right - left);

        const y =
            bottom -
            (
                (Number(item.temperature_c) - minTemp)
                / range
            ) *
            (bottom - top);

        return {
            x,
            y,
            temperature: Number(item.temperature_c),
            day: item.day
        };
    });

    const polylinePoints = points
        .map(point => `${point.x},${point.y}`)
        .join(" ");

    const circles = points
        .map(point => `
            <circle
                cx="${point.x}"
                cy="${point.y}"
                r="4"
                fill="#2563eb"
            >
                <title>
                    Day ${point.day}: ${point.temperature.toFixed(1)}°C
                </title>
            </circle>
        `)
        .join("");

    svg.innerHTML = `
        <polyline
            fill="none"
            stroke="#2563eb"
            stroke-width="4"
            points="${polylinePoints}"
        />

        ${circles}
    `;
}


function renderRainfall(data) {

    const container =
        document.getElementById("rainfallBars");

    if (!container) {
        return;
    }

    const rainfall =
        data.monthly_rainfall || [];

    if (rainfall.length === 0) {
        container.innerHTML =
            "<p>No rainfall data available.</p>";
        return;
    }

    const maxRainfall = Math.max(
        ...rainfall.map(
            item => Number(item.rainfall_mm)
        ),
        1
    );

    container.innerHTML = rainfall.map(item => {

        const value =
            Number(item.rainfall_mm);

        const height =
            Math.max(
                3,
                (value / maxRainfall) * 100
            );

        return `
            <div class="rain-bar-item">

                <div
                    class="rain-bar"
                    style="height:${height}%"
                    title="${value.toFixed(1)} mm"
                ></div>

                <p>${item.month}</p>

            </div>
        `;

    }).join("");
}


function renderAnalytics(data) {

    document.getElementById(
        "analyticsLocation"
    ).textContent =
        `Insights for ${data.location}`;

    document.getElementById(
        "analyticsMonth"
    ).textContent =
        `${data.month_name} ${data.year}`;

    document.getElementById(
        "highestTemp"
    ).textContent =
        `${formatNumber(
            data.highest_temperature_c,
            1
        )}°C`;

    document.getElementById(
        "lowestTemp"
    ).textContent =
        `${formatNumber(
            data.lowest_temperature_c,
            1
        )}°C`;

    document.getElementById(
        "rainfallValue"
    ).textContent =
        `${formatNumber(
            data.total_rainfall_mm,
            1
        )} mm`;

    document.getElementById(
        "humidityValue"
    ).textContent =
        `${formatNumber(
            data.average_humidity_percent,
            0
        )}%`;

    document.getElementById(
        "dryDays"
    ).textContent =
        data.dry_days;

    document.getElementById(
        "rainyDays"
    ).textContent =
        data.rainy_days;

    document.getElementById(
        "humidityInsight"
    ).textContent =
        `${formatNumber(
            data.average_humidity_percent,
            0
        )}%`;

    document.getElementById(
        "windInsight"
    ).textContent =
        `${formatNumber(
            data.average_wind_speed_kmh,
            1
        )} km/h`;

    document.getElementById(
        "highestTime"
    ).textContent =
        formatDateTime(
            data.highest_temperature_time
        );

    document.getElementById(
        "lowestTime"
    ).textContent =
        formatDateTime(
            data.lowest_temperature_time
        );

    document.getElementById(
        "dataPeriod"
    ).textContent =
        `${data.data_start} to ${data.data_end}`;

    renderTemperatureChart(data);

    renderRainfall(data);
}


async function loadAnalytics() {

    const url =
        `${API_BASE}/api/v1/chat/analytics` +
        `?city=${encodeURIComponent(CITY)}` +
        `&year=${YEAR}` +
        `&month=${MONTH}`;

    console.log("Analytics API:", url);

    try {

        const response =
            await fetch(url);

        if (!response.ok) {

            const errorText =
                await response.text();

            throw new Error(
                `HTTP ${response.status}: ${errorText}`
            );
        }

        const data =
            await response.json();

        console.log(
            "Analytics API response:",
            data
        );

        renderAnalytics(data);

        console.log(
            "Analytics page loaded successfully."
        );

    } catch (error) {

        console.error(
            "Analytics API error:",
            error
        );

        const status =
            document.getElementById(
                "analyticsStatus"
            );

        if (status) {
            status.textContent =
                "Unable to load analytics data.";
        }
    }
}


document.addEventListener(
    "DOMContentLoaded",
    () => {

        const cards =
            document.querySelectorAll(
                ".stat-card"
            );

        cards.forEach(card => {

            card.addEventListener(
                "mouseenter",
                () => {
                    card.style.transform =
                        "translateY(-5px)";
                }
            );

            card.addEventListener(
                "mouseleave",
                () => {
                    card.style.transform =
                        "translateY(0px)";
                }
            );

        });

        loadAnalytics();
    }
);
