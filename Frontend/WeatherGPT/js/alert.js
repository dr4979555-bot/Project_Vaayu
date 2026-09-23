const API_BASE_URL = "https://project-vaayu.onrender.com";

const FALLBACK_LOCATION = {
    latitude: 25.5941,
    longitude: 85.1376,
    name: "Patna, Bihar"
};


// ------------------------------------------------------------
// Get browser location
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
// Map severity to visual class
// ------------------------------------------------------------
function getSeverityClass(severity) {

    const value =
        String(severity || "").toLowerCase();

    if (
        value === "extreme" ||
        value === "severe"
    ) {
        return "red";
    }

    if (
        value === "moderate" ||
        value === "warning"
    ) {
        return "orange";
    }

    return "yellow";
}


// ------------------------------------------------------------
// Create one alert card
// ------------------------------------------------------------
function createAlertCard(alert) {

    const card =
        document.createElement("div");

    const severityClass =
        getSeverityClass(
            alert.severity
        );

    card.className =
        `alert-card ${severityClass}`;

    card.innerHTML = `
        <div class="tag">
            ${alert.severity || "INFO"} ALERT
        </div>

        <h3>
            ${alert.event_category || "Weather Alert"}
        </h3>

        <p>
            ${alert.headline || "Active weather alert."}
        </p>

        ${
            alert.instruction
                ? `<small>${alert.instruction}</small>`
                : ""
        }
    `;

    return card;
}


// ------------------------------------------------------------
// Load active alerts
// ------------------------------------------------------------
async function loadAlerts() {

    try {

        const location =
            await getBrowserLocation();


        const url =
            `${API_BASE_URL}/api/v1/alerts/active` +
            `?latitude=${encodeURIComponent(
                location.latitude
            )}` +
            `&longitude=${encodeURIComponent(
                location.longitude
            )}` +
            `&radius_km=50`;


        console.log(
            "Alerts API:",
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
                "Unable to fetch active alerts."
            );
        }


        console.log(
            "Active alerts response:",
            data
        );


        // ----------------------------------------------------
        // Location
        // ----------------------------------------------------

        const heroLocation =
            document.getElementById(
                "heroAlertLocation"
            );

        if (heroLocation) {

            heroLocation.textContent =
                location.name;
        }


        // ----------------------------------------------------
        // Alert status
        // ----------------------------------------------------

        const alertStatus =
            document.getElementById(
                "alertStatus"
            );


        const heroTitle =
            document.getElementById(
                "heroAlertTitle"
            );


        const heroTime =
            document.getElementById(
                "heroAlertTime"
            );


        const heroIcon =
            document.getElementById(
                "heroAlertIcon"
            );


        const alertGrid =
            document.getElementById(
                "alertGrid"
            );


        const timelineTitle =
            document.getElementById(
                "timelineTitle"
            );


        const timelineMessage =
            document.getElementById(
                "timelineMessage"
            );


        // ----------------------------------------------------
        // NO ACTIVE ALERTS
        // ----------------------------------------------------

        if (!Array.isArray(data) || data.length === 0) {

            if (alertStatus) {

                alertStatus.innerHTML =
                    '<i class="fa-solid fa-circle"></i> ' +
                    'Live Monitoring';
            }


            if (heroTitle) {

                heroTitle.textContent =
                    "No Active Alerts";
            }


            if (heroTime) {

                heroTime.textContent =
                    "No active CAP alerts found within 50 km.";
            }


            if (heroIcon) {

                heroIcon.className =
                    "fa-solid fa-circle-check";
            }


            if (alertGrid) {

                alertGrid.innerHTML = `
                    <div class="alert-card yellow">

                        <div class="tag">
                            CLEAR
                        </div>

                        <h3>
                            No Active Weather Alerts
                        </h3>

                        <p>
                            No active registered weather
                            or disaster alerts were found
                            for this location.
                        </p>

                    </div>
                `;
            }


            if (timelineTitle) {

                timelineTitle.textContent =
                    "No Active Alerts";
            }


            if (timelineMessage) {

                timelineMessage.textContent =
                    "Vaayu is monitoring registered alerts for this location.";
            }


            console.log(
                "No active weather alerts."
            );

            return;
        }


        // ----------------------------------------------------
        // ACTIVE ALERTS FOUND
        // ----------------------------------------------------

        const latestAlert =
            data[0];


        if (alertStatus) {

            alertStatus.innerHTML =
                '<i class="fa-solid fa-circle"></i> ' +
                `${data.length} Active Alert` +
                `${data.length > 1 ? "s" : ""}`;
        }


        if (heroTitle) {

            heroTitle.textContent =
                latestAlert.headline ||
                latestAlert.event_category ||
                "Active Weather Alert";
        }


        if (heroTime) {

            heroTime.textContent =
                latestAlert.sent_at
                    ? `Issued: ${new Date(
                        latestAlert.sent_at
                    ).toLocaleString()}`
                    : "Active alert";
        }


        if (heroIcon) {

            const severity =
                String(
                    latestAlert.severity || ""
                ).toLowerCase();

            if (
                severity === "extreme" ||
                severity === "severe"
            ) {

                heroIcon.className =
                    "fa-solid fa-triangle-exclamation";

            } else {

                heroIcon.className =
                    "fa-solid fa-cloud-showers-heavy";
            }
        }


        if (alertGrid) {

            alertGrid.innerHTML = "";

            data.forEach(
                (alert) => {

                    alertGrid.appendChild(
                        createAlertCard(alert)
                    );
                }
            );
        }


        if (timelineTitle) {

            timelineTitle.textContent =
                latestAlert.event_category ||
                "Weather Alert";
        }


        if (timelineMessage) {

            timelineMessage.textContent =
                latestAlert.instruction ||
                latestAlert.headline ||
                "Follow official authority instructions.";
        }

    }

    catch (error) {

        console.error(
            "Alerts API error:",
            error
        );


        const heroTitle =
            document.getElementById(
                "heroAlertTitle"
            );

        const heroTime =
            document.getElementById(
                "heroAlertTime"
            );

        const alertGrid =
            document.getElementById(
                "alertGrid"
            );


        if (heroTitle) {

            heroTitle.textContent =
                "Alert Service Unavailable";
        }


        if (heroTime) {

            heroTime.textContent =
                "Unable to retrieve active alerts.";
        }


        if (alertGrid) {

            alertGrid.innerHTML = `
                <div class="alert-card orange">

                    <div class="tag">
                        UNAVAILABLE
                    </div>

                    <h3>
                        Alert Data Unavailable
                    </h3>

                    <p>
                        Vaayu could not retrieve the
                        latest registered alerts.
                    </p>

                </div>
            `;
        }
    }
}


// ------------------------------------------------------------
// Emergency buttons
// ------------------------------------------------------------
function setupEmergencyButtons() {

    const emergencyButton =
        document.getElementById(
            "emergencyButton"
        );

    const shelterButton =
        document.getElementById(
            "shelterButton"
        );

    const enableAlertButton =
        document.getElementById(
            "enableAlertButton"
        );


    if (emergencyButton) {

        emergencyButton.addEventListener(
            "click",
            () => {

                window.location.href =
                    "tel:112";
            }
        );
    }


    if (shelterButton) {

        shelterButton.addEventListener(
            "click",
            () => {

                alert(
                    "Nearest shelter information " +
                    "is not currently available " +
                    "from the backend."
                );
            }
        );
    }


    if (enableAlertButton) {

        enableAlertButton.addEventListener(
            "click",
            () => {

                if (
                    "Notification" in window
                ) {

                    Notification.requestPermission()
                        .then(
                            (permission) => {

                                if (
                                    permission ===
                                    "granted"
                                ) {

                                    alert(
                                        "Browser notifications enabled."
                                    );

                                } else {

                                    alert(
                                        "Notification permission was not granted."
                                    );
                                }
                            }
                        );

                } else {

                    alert(
                        "Browser notifications are not supported."
                    );
                }
            }
        );
    }
}


// ------------------------------------------------------------
// Start
// ------------------------------------------------------------
document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadAlerts();
        setupEmergencyButtons();

    }
);
