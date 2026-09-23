const API_BASE_URL = "https://project-vaayu.onrender.com";

const CITY = "Patna";


function createSvgElement(tag) {
    return document.createElementNS(
        "http://www.w3.org/2000/svg",
        tag
    );
}


function renderClimateChart(monthlyData) {

    const svg =
        document.getElementById(
            "climateChart"
        );

    if (!svg || !monthlyData.length) {
        return;
    }

    svg.innerHTML = "";

    const width = 700;
    const height = 250;

    const paddingLeft = 45;
    const paddingRight = 25;
    const paddingTop = 25;
    const paddingBottom = 35;

    const chartWidth =
        width -
        paddingLeft -
        paddingRight;

    const chartHeight =
        height -
        paddingTop -
        paddingBottom;

    const values =
        monthlyData.map(
            item =>
                Number(
                    item.average_temperature_c
                )
        );

    const minValue =
        Math.min(...values);

    const maxValue =
        Math.max(...values);

    const range =
        Math.max(
            maxValue - minValue,
            1
        );


    const points =
        monthlyData.map(
            (item, index) => {

                const x =
                    paddingLeft +
                    (
                        index /
                        Math.max(
                            monthlyData.length - 1,
                            1
                        )
                    ) *
                    chartWidth;

                const y =
                    paddingTop +
                    chartHeight -
                    (
                        (
                            Number(
                                item.average_temperature_c
                            ) -
                            minValue
                        ) /
                        range
                    ) *
                    chartHeight;

                return {
                    x,
                    y,
                    value:
                        Number(
                            item.average_temperature_c
                        )
                };
            }
        );


    // Line
    const polyline =
        createSvgElement(
            "polyline"
        );

    polyline.setAttribute(
        "fill",
        "none"
    );

    polyline.setAttribute(
        "stroke",
        "#2563eb"
    );

    polyline.setAttribute(
        "stroke-width",
        "4"
    );

    polyline.setAttribute(
        "points",
        points
            .map(
                point =>
                    `${point.x},${point.y}`
            )
            .join(" ")
    );

    svg.appendChild(
        polyline
    );


    // Points
    points.forEach(
        point => {

            const circle =
                createSvgElement(
                    "circle"
                );

            circle.setAttribute(
                "cx",
                point.x
            );

            circle.setAttribute(
                "cy",
                point.y
            );

            circle.setAttribute(
                "r",
                "5"
            );

            circle.setAttribute(
                "fill",
                "#2563eb"
            );

            svg.appendChild(
                circle
            );
        }
    );
}


async function loadClimateData() {

    try {

        const url =
            `${API_BASE_URL}/api/v1/chat/climate` +
            `?city=${encodeURIComponent(CITY)}`;


        console.log(
            "Climate API:",
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
                "Unable to fetch climate data."
            );
        }


        console.log(
            "Climate API response:",
            data
        );


        // ----------------------------------------------------
        // Location
        // ----------------------------------------------------

        const locationElement =
            document.getElementById(
                "climateLocation"
            );

        if (locationElement) {

            locationElement.innerHTML = `
                <i class="fa-solid fa-location-dot"></i>
                ${data.location}, Bihar
            `;
        }


        // ----------------------------------------------------
        // Statistics
        // ----------------------------------------------------

        document.getElementById(
            "avgSummerHigh"
        ).textContent =
            `${data.average_summer_high_c.toFixed(2)}°C`;


        document.getElementById(
            "annualRainfall"
        ).textContent =
            `${data.average_annual_rainfall_mm.toFixed(2)} mm`;


        document.getElementById(
            "hottestDay"
        ).textContent =
            `${data.hottest_day.temperature_c.toFixed(1)}°C`;


        document.getElementById(
            "daysAbove40"
        ).textContent =
            data.days_40_plus_c;


        // ----------------------------------------------------
        // Bottom insights
        // ----------------------------------------------------

        document.getElementById(
            "hottestDate"
        ).textContent =
            `${data.hottest_day.date}`;


        document.getElementById(
            "rainfallInsight"
        ).textContent =
            `${data.average_annual_rainfall_mm.toFixed(1)} mm`;


        document.getElementById(
            "summerInsight"
        ).textContent =
            `${data.average_summer_high_c.toFixed(1)}°C`;


        document.getElementById(
            "periodInsight"
        ).textContent =
            `${data.data_start.slice(0, 4)}–${data.data_end.slice(0, 4)}`;


        document.getElementById(
            "dataCoverage"
        ).textContent =
            `${data.data_start.slice(0, 4)}–${data.data_end.slice(0, 4)}`;


        // ----------------------------------------------------
        // Temperature trend
        // ----------------------------------------------------

        renderClimateChart(
            data.monthly_temperature_trend
        );


        console.log(
            "Climate page loaded successfully."
        );

    }

    catch (error) {

        console.error(
            "Climate API error:",
            error
        );

        document.getElementById(
            "avgSummerHigh"
        ).textContent =
            "--°C";

        document.getElementById(
            "annualRainfall"
        ).textContent =
            "-- mm";

        document.getElementById(
            "hottestDay"
        ).textContent =
            "--°C";

        document.getElementById(
            "daysAbove40"
        ).textContent =
            "--";
    }
}


document.addEventListener(
    "DOMContentLoaded",
    loadClimateData
);
