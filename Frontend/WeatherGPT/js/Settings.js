console.log("Settings page loaded");


/* =========================
   Elements
========================= */

const darkToggle = document.getElementById("darkToggle");
const saveBtn = document.getElementById("saveBtn");

const editBtn = document.getElementById("editProfileBtn");
const modal = document.getElementById("profileModal");
const closeBtn = document.getElementById("closeModal");
const saveProfile = document.getElementById("saveProfile");

const profileName = document.getElementById("profileName");
const profileCity = document.getElementById("profileCity");

const nameInput = document.getElementById("nameInput");
const cityInput = document.getElementById("cityInput");

const locationInput =
    document.getElementById("locationInput");

const languageSelect =
    document.getElementById("languageSelect");

const tempUnit =
    document.getElementById("tempUnit");

const alertToggle =
    document.getElementById("alertToggle");

const refreshSelect =
    document.getElementById("refreshSelect");


/* =========================
   Load Saved Settings
========================= */

function loadSettings() {

    const saved =
        localStorage.getItem("vaayuSettings");

    if (!saved) {
        return;
    }

    try {

        const settings =
            JSON.parse(saved);

        if (
            darkToggle &&
            typeof settings.darkMode === "boolean"
        ) {
            darkToggle.checked =
                settings.darkMode;

            document.body.classList.toggle(
                "dark",
                settings.darkMode
            );
        }

        if (
            locationInput &&
            settings.location !== undefined
        ) {
            locationInput.value =
                settings.location;
        }

        if (
            languageSelect &&
            settings.language !== undefined
        ) {
            languageSelect.value =
                settings.language;
        }

        if (
            tempUnit &&
            settings.tempUnit !== undefined
        ) {
            tempUnit.value =
                settings.tempUnit;
        }

        if (
            alertToggle &&
            typeof settings.alerts === "boolean"
        ) {
            alertToggle.checked =
                settings.alerts;
        }

        if (
            refreshSelect &&
            settings.refresh !== undefined
        ) {
            refreshSelect.value =
                settings.refresh;
        }

    } catch (error) {

        console.error(
            "Unable to load saved settings:",
            error
        );
    }
}


/* =========================
   Dark Mode
========================= */

if (darkToggle) {

    darkToggle.addEventListener(
        "change",
        () => {

            document.body.classList.toggle(
                "dark",
                darkToggle.checked
            );

        }
    );
}


/* =========================
   Edit Profile Modal
========================= */

if (editBtn && modal) {

    editBtn.addEventListener(
        "click",
        () => {

            modal.classList.add(
                "active"
            );

        }
    );
}


if (closeBtn && modal) {

    closeBtn.addEventListener(
        "click",
        () => {

            modal.classList.remove(
                "active"
            );

        }
    );
}


if (modal) {

    window.addEventListener(
        "click",
        event => {

            if (event.target === modal) {

                modal.classList.remove(
                    "active"
                );

            }

        }
    );
}


/* =========================
   Save Profile
========================= */

if (
    saveProfile &&
    modal
) {

    saveProfile.addEventListener(
        "click",
        () => {

            if (
                profileName &&
                nameInput
            ) {
                profileName.innerText =
                    nameInput.value.trim();
            }

            if (
                profileCity &&
                cityInput
            ) {
                profileCity.innerText =
                    cityInput.value.trim();
            }

            modal.classList.remove(
                "active"
            );

            alert(
                "Profile Updated Successfully!"
            );

        }
    );
}


/* =========================
   Save Changes
========================= */

if (saveBtn) {

    saveBtn.addEventListener(
        "click",
        () => {

            const settings = {

                darkMode:
                    darkToggle
                        ? darkToggle.checked
                        : false,

                location:
                    locationInput
                        ? locationInput.value
                        : "",

                language:
                    languageSelect
                        ? languageSelect.value
                        : "",

                tempUnit:
                    tempUnit
                        ? tempUnit.value
                        : "",

                alerts:
                    alertToggle
                        ? alertToggle.checked
                        : false,

                refresh:
                    refreshSelect
                        ? refreshSelect.value
                        : ""
            };


            localStorage.setItem(
                "vaayuSettings",
                JSON.stringify(settings)
            );


            const originalText =
                saveBtn.innerHTML;

            const originalBackground =
                saveBtn.style.background;


            saveBtn.innerHTML =
                '<i class="fa-solid fa-check"></i> Saved';

            saveBtn.style.background =
                "#16a34a";


            setTimeout(
                () => {

                    saveBtn.innerHTML =
                        originalText;

                    saveBtn.style.background =
                        originalBackground;

                },
                2000
            );

        }
    );
}


/* =========================
   Initial Load
========================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadSettings();

        console.log(
            "Settings initialized successfully."
        );

    }
);
