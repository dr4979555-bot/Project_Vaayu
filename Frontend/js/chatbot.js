const API_BASE_URL = "https://project-vaayu.onrender.com";

const FALLBACK_LOCATION = {
    latitude: 25.5941,
    longitude: 85.1376
};


const chatArea =
    document.getElementById("chatArea");

const input =
    document.getElementById("messageInput");

const sendBtn =
    document.getElementById("sendBtn");

const micBtn =
    document.getElementById("micBtn");

const typing =
    document.getElementById("typing");

const voiceStatus =
    document.getElementById("voiceStatus");

const voiceLanguage =
    document.getElementById("voiceLanguage");


let mediaRecorder = null;

let audioChunks = [];

let mediaStream = null;

let isRecording = false;


/* =========================
   Utility
========================= */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text ?? "";

    return div.innerHTML;
}


function setTyping(visible) {

    if (!typing) {
        return;
    }

    typing.style.visibility =
        visible ? "visible" : "hidden";
}


function setVoiceStatus(
    text,
    icon = "fa-microphone"
) {

    if (!voiceStatus) {
        return;
    }

    voiceStatus.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        ${escapeHtml(text)}
    `;
}


function scrollChat() {

    if (!chatArea) {
        return;
    }

    chatArea.scrollTop =
        chatArea.scrollHeight;
}


/* =========================
   Messages
========================= */

function addUserMessage(text) {

    const message =
        document.createElement("div");

    message.className =
        "user message";

    message.innerHTML = `
        <div class="bubble">
            ${escapeHtml(text)}
        </div>

        <div class="avatar user-avatar">
            U
        </div>
    `;

    chatArea.appendChild(message);

    scrollChat();
}


function addBotMessage(
    text,
    audioBase64 = null
) {

    const message =
        document.createElement("div");

    message.className =
        "bot message";


    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar";

    avatar.textContent =
        "AI";


    const bubble =
        document.createElement("div");

    bubble.className =
        "bubble";

    bubble.textContent =
        text;


    message.appendChild(
        avatar
    );

    message.appendChild(
        bubble
    );


    if (audioBase64) {

        const replayBtn =
            document.createElement("button");

        replayBtn.className =
            "replay-btn";

        replayBtn.title =
            "Play voice response";

        replayBtn.innerHTML =
            '<i class="fa-solid fa-volume-high"></i>';


        replayBtn.addEventListener(
            "click",
            () => {

                playAudio(
                    audioBase64
                );

            }
        );


        bubble.appendChild(
            document.createElement("br")
        );

        bubble.appendChild(
            replayBtn
        );


        // Try automatic playback.
        playAudio(audioBase64);
    }


    chatArea.appendChild(
        message
    );

    scrollChat();
}


function addErrorMessage(text) {

    addBotMessage(
        `Sorry, I couldn't process that request.\n\n${text}`
    );
}


/* =========================
   Browser Location
========================= */

function getBrowserLocation() {

    return new Promise(
        resolve => {

            if (!navigator.geolocation) {

                resolve(
                    FALLBACK_LOCATION
                );

                return;
            }


            navigator.geolocation.getCurrentPosition(

                position => {

                    resolve({
                        latitude:
                            position.coords.latitude,

                        longitude:
                            position.coords.longitude
                    });

                },

                () => {

                    console.warn(
                        "Browser location unavailable. Using Patna fallback."
                    );

                    resolve(
                        FALLBACK_LOCATION
                    );

                },

                {
                    enableHighAccuracy: false,
                    timeout: 5000,
                    maximumAge: 300000
                }
            );

        }
    );
}


/* =========================
   Audio Playback
========================= */

function playAudio(
    audioBase64
) {

    if (!audioBase64) {
        return;
    }


    try {

        const binaryString =
            atob(audioBase64);

        const byteArray =
            new Uint8Array(
                binaryString.length
            );


        for (
            let index = 0;
            index < binaryString.length;
            index++
        ) {

            byteArray[index] =
                binaryString.charCodeAt(index);

        }


        const blob =
            new Blob(
                [byteArray],
                {
                    type: "audio/mpeg"
                }
            );


        const audioUrl =
            URL.createObjectURL(blob);


        const audio =
            new Audio(audioUrl);


        audio.onended = () => {

            URL.revokeObjectURL(
                audioUrl
            );

        };


        audio.onerror = () => {

            URL.revokeObjectURL(
                audioUrl
            );

            console.warn(
                "Unable to play generated voice audio."
            );

        };


        const playPromise =
            audio.play();


        if (
            playPromise &&
            typeof playPromise.catch === "function"
        ) {

            playPromise.catch(
                error => {

                    console.warn(
                        "Automatic audio playback was blocked:",
                        error
                    );

                    setVoiceStatus(
                        "Voice response ready — tap the speaker button to play.",
                        "fa-volume-high"
                    );

                }
            );
        }

    } catch (error) {

        console.error(
            "Audio playback error:",
            error
        );

    }
}


/* =========================
   Chat API
========================= */

async function sendQuery(
    text
) {

    if (!text || text.trim() === "") {
        return;
    }


    addUserMessage(text);


    setTyping(true);

    sendBtn.disabled = true;

    if (micBtn) {
        micBtn.disabled = true;
    }


    try {

        const location =
            await getBrowserLocation();


        const selectedLanguage =
            voiceLanguage
                ? voiceLanguage.value
                : "en";


        const response =
            await fetch(
                `${API_BASE_URL}/api/v1/chat/message`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body: JSON.stringify({

                        query:
                            text,

                        latitude:
                            location.latitude,

                        longitude:
                            location.longitude,

                        language:
                            selectedLanguage,

                        include_voice:
                            true

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            let errorMessage =
                "Backend request failed.";


            if (
                data &&
                data.detail
            ) {

                errorMessage =
                    typeof data.detail === "string"
                        ? data.detail
                        : JSON.stringify(
                            data.detail
                        );

            }


            throw new Error(
                errorMessage
            );

        }


        if (!data.response) {

            throw new Error(
                "Backend returned an empty response."
            );

        }


        addBotMessage(
            data.response,
            data.audio_base64 || null
        );


        if (data.audio_base64) {

            setVoiceStatus(
                "Voice response generated.",
                "fa-volume-high"
            );

        } else {

            setVoiceStatus(
                "Text response received. Voice was unavailable.",
                "fa-comment"
            );

        }

    } catch (error) {

        console.error(
            "WeatherGPT API error:",
            error
        );


        addErrorMessage(
            error.message ||
            "Unable to connect to the WeatherGPT backend."
        );


        setVoiceStatus(
            "Voice response unavailable.",
            "fa-triangle-exclamation"
        );

    } finally {

        setTyping(false);

        sendBtn.disabled = false;

        if (micBtn) {
            micBtn.disabled = false;
        }

        input.focus();
    }
}


/* =========================
   Text Message
========================= */

async function sendMessage() {

    const text =
        input.value.trim();


    if (text === "") {
        return;
    }


    input.value = "";


    await sendQuery(
        text
    );
}


/* =========================
   Voice Transcription
========================= */

async function transcribeAudio(
    audioBlob
) {

    const selectedLanguage =
        voiceLanguage
            ? voiceLanguage.value
            : "en";


    setTyping(true);

    setVoiceStatus(
        "Transcribing your voice...",
        "fa-spinner"
    );


    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/v1/chat/voice/transcribe` +
                `?language=${encodeURIComponent(
                    selectedLanguage
                )}`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            audioBlob.type ||
                            "audio/webm"
                    },

                    body:
                        audioBlob
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            const message =
                data && data.detail
                    ? data.detail
                    : "Voice transcription failed.";

            throw new Error(
                typeof message === "string"
                    ? message
                    : JSON.stringify(message)
            );

        }


        if (!data.text) {

            throw new Error(
                "No speech was detected."
            );

        }


        const transcript =
            data.text.trim();


        setVoiceStatus(
            `Heard: "${transcript}"`,
            "fa-check"
        );


        await sendQuery(
            transcript
        );


    } catch (error) {

        console.error(
            "Voice transcription error:",
            error
        );


        setTyping(false);

        setVoiceStatus(
            error.message ||
            "Unable to transcribe your voice.",
            "fa-triangle-exclamation"
        );

        addErrorMessage(
            error.message ||
            "Unable to transcribe your voice."
        );

    }
}


/* =========================
   Start Recording
========================= */

async function startRecording() {

    if (isRecording) {
        return;
    }


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        alert(
            "Microphone recording is not supported by this browser."
        );

        return;
    }


    if (
        typeof MediaRecorder ===
        "undefined"
    ) {

        alert(
            "Voice recording is not supported by this browser."
        );

        return;
    }


    try {

        mediaStream =
            await navigator.mediaDevices.getUserMedia({
                audio: true
            });


        let options = {};


        if (
            MediaRecorder.isTypeSupported(
                "audio/webm;codecs=opus"
            )
        ) {

            options.mimeType =
                "audio/webm;codecs=opus";

        } else if (
            MediaRecorder.isTypeSupported(
                "audio/webm"
            )
        ) {

            options.mimeType =
                "audio/webm";
        }


        mediaRecorder =
            new MediaRecorder(
                mediaStream,
                options
            );


        audioChunks = [];

        isRecording = true;


        mediaRecorder.addEventListener(
            "dataavailable",
            event => {

                if (
                    event.data &&
                    event.data.size > 0
                ) {

                    audioChunks.push(
                        event.data
                    );
                }

            }
        );


        mediaRecorder.addEventListener(
            "stop",
            async () => {

                const mimeType =
                    mediaRecorder.mimeType ||
                    "audio/webm";


                const audioBlob =
                    new Blob(
                        audioChunks,
                        {
                            type: mimeType
                        }
                    );


                if (mediaStream) {

                    mediaStream
                        .getTracks()
                        .forEach(
                            track =>
                                track.stop()
                        );

                }


                mediaStream = null;

                mediaRecorder = null;

                isRecording = false;


                micBtn.classList.remove(
                    "recording"
                );


                micBtn.innerHTML =
                    '<i class="fa-solid fa-microphone"></i>';


                if (
                    audioBlob.size === 0
                ) {

                    setVoiceStatus(
                        "No audio was recorded.",
                        "fa-triangle-exclamation"
                    );

                    return;
                }


                await transcribeAudio(
                    audioBlob
                );

            }
        );


        mediaRecorder.start();


        micBtn.classList.add(
            "recording"
        );


        micBtn.innerHTML =
            '<i class="fa-solid fa-stop"></i>';


        setVoiceStatus(
            "Listening... click the microphone again to stop.",
            "fa-microphone"
        );


    } catch (error) {

        console.error(
            "Microphone access error:",
            error
        );


        if (mediaStream) {

            mediaStream
                .getTracks()
                .forEach(
                    track =>
                        track.stop()
                );

        }


        mediaStream = null;


        alert(
            "Microphone permission was denied or unavailable."
        );


        setVoiceStatus(
            "Microphone unavailable.",
            "fa-triangle-exclamation"
        );
    }
}


/* =========================
   Stop Recording
========================= */

function stopRecording() {

    if (
        mediaRecorder &&
        isRecording
    ) {

        mediaRecorder.stop();

    }
}


/* =========================
   Mic Button
========================= */

micBtn.addEventListener(
    "click",
    () => {

        if (isRecording) {

            stopRecording();

        } else {

            startRecording();

        }

    }
);


/* =========================
   Send Button
========================= */

sendBtn.addEventListener(
    "click",
    sendMessage
);


/* =========================
   Enter Key
========================= */

input.addEventListener(
    "keypress",
    event => {

        if (
            event.key === "Enter"
        ) {

            sendMessage();

        }

    }
);


/* =========================
   Suggestions
========================= */

document
    .querySelectorAll(
        ".suggestions button"
    )
    .forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    const text =
                        button.innerText.trim();

                    input.value = "";

                    sendQuery(
                        text
                    );

                }
            );

        }
    );


/* =========================
   Initial State
========================= */

setVoiceStatus(
    "Ready for voice input.",
    "fa-microphone"
);
