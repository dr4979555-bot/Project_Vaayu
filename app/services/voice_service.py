import base64
import logging
from typing import Dict, Any, Optional

import httpx
from groq import AsyncGroq
import edge_tts

from app.config import settings


logger = logging.getLogger("WeatherGPT.VoiceService")


# High-fidelity Microsoft Neural Indic Voices
_INDIC_NEURAL_VOICES: Dict[str, Dict[str, str]] = {
    "hi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
    },
    "bn": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural",
    },
    "mr": {
        "female": "mr-IN-AarohiNeural",
        "male": "mr-IN-ManoharNeural",
    },
    "en": {
        "female": "en-IN-NeerjaNeural",
        "male": "en-IN-PrabhatNeural",
    },
    "ta": {
        "female": "ta-IN-PallaviNeural",
        "male": "ta-IN-ValluvarNeural",
    },
    "te": {
        "female": "te-IN-ShrutiNeural",
        "male": "te-IN-MohanNeural",
    },
}


# Bhashini ULCA API
BHASHINI_ULCA_COMPUTE_URL = (
    "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
)


class VoiceService:
    """
    Voice pipeline for Vaayu.

    Speech-to-Text:
    1. Bhashini ULCA ASR when credentials are configured.
    2. Groq Whisper Large v3 Turbo fallback.

    Text-to-Speech:
    1. Bhashini ULCA TTS when credentials are configured.
    2. Microsoft Neural Voices through edge-tts fallback.
    """

    # ------------------------------------------------------------------
    # Voice Selection
    # ------------------------------------------------------------------

    @classmethod
    def get_voice_name(
        cls,
        language: str,
        gender: str = "female",
    ) -> str:
        """
        Return Microsoft Neural voice identifier.
        """

        lang = (language or "en").lower()

        if lang not in _INDIC_NEURAL_VOICES:
            lang = "en"

        selected_gender = gender.lower()

        if selected_gender not in _INDIC_NEURAL_VOICES[lang]:
            selected_gender = "female"

        return _INDIC_NEURAL_VOICES[lang][selected_gender]

    # ------------------------------------------------------------------
    # Groq Client
    # ------------------------------------------------------------------

    @classmethod
    def _get_groq_client(cls) -> AsyncGroq:
        """
        Create a fresh Groq client from the current application settings.

        A fresh client avoids keeping a stale API key in a module-level
        client object.
        """

        api_key = settings.GROQ_API_KEY

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        return AsyncGroq(
            api_key=api_key.strip()
        )

    # ------------------------------------------------------------------
    # Speech-to-Text (ASR)
    # ------------------------------------------------------------------

    @classmethod
    async def transcribe_audio(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert recorded audio into text.

        Priority:
        1. Bhashini ULCA ASR
        2. Groq Whisper Large v3 Turbo
        """

        if not audio_bytes:
            raise RuntimeError(
                "Audio data is empty."
            )

        selected_language = (
            language
            if language in ("hi", "bn", "mr", "en")
            else None
        )

        # --------------------------------------------------------------
        # Tier 1: Bhashini
        # --------------------------------------------------------------

        if (
            settings.BHASHINI_USER_ID
            and settings.BHASHINI_API_KEY
            and settings.BHASHINI_PIPELINE_ID
        ):
            try:
                bhashini_result = await cls._bhashini_asr(
                    audio_bytes=audio_bytes,
                    language=selected_language or "hi",
                )

                if bhashini_result:
                    logger.info(
                        "Bhashini ASR transcription successful."
                    )

                    return bhashini_result

            except Exception as exc:
                logger.warning(
                    "Bhashini ASR failed. "
                    f"Falling back to Groq Whisper: {exc}"
                )

        # --------------------------------------------------------------
        # Tier 2: Groq Whisper
        # --------------------------------------------------------------

        try:
            groq_client = cls._get_groq_client()

            transcription = (
                await groq_client.audio.transcriptions.create(
                    file=(
                        filename,
                        audio_bytes,
                    ),
                    model="whisper-large-v3-turbo",
                    language=selected_language,
                    response_format="json",
                )
            )

            text = (
                transcription.text.strip()
                if transcription.text
                else ""
            )

            if not text:
                raise RuntimeError(
                    "Whisper returned an empty transcription."
                )

            logger.info(
                "Groq Whisper transcribed "
                f"{len(audio_bytes)} bytes -> '{text}'"
            )

            return {
                "text": text,
                "language": (
                    language
                    if language
                    else "detected"
                ),
                "engine": (
                    "Groq-Whisper-Large-v3-Turbo"
                ),
            }

        except Exception as exc:
            logger.error(
                "Whisper transcription failed: "
                f"{type(exc).__name__}: {exc}",
                exc_info=True,
            )

            raise RuntimeError(
                f"Audio transcription failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Text-to-Speech (TTS)
    # ------------------------------------------------------------------

    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        language: str = "hi",
        gender: str = "female",
    ) -> bytes:
        """
        Convert text into MP3 audio.

        Priority:
        1. Bhashini ULCA TTS
        2. Microsoft Neural Voice through edge-tts
        """

        if not text or not text.strip():
            raise RuntimeError(
                "Speech text is empty."
            )

        # --------------------------------------------------------------
        # Tier 1: Bhashini
        # --------------------------------------------------------------

        if (
            settings.BHASHINI_USER_ID
            and settings.BHASHINI_API_KEY
            and settings.BHASHINI_PIPELINE_ID
        ):
            try:
                bhashini_audio = (
                    await cls._bhashini_tts(
                        text=text,
                        language=language,
                        gender=gender,
                    )
                )

                if bhashini_audio:
                    logger.info(
                        "Bhashini TTS synthesis successful."
                    )

                    return bhashini_audio

            except Exception as exc:
                logger.warning(
                    "Bhashini TTS failed. "
                    f"Falling back to edge-tts: {exc}"
                )

        # --------------------------------------------------------------
        # Tier 2: Microsoft Neural TTS
        # --------------------------------------------------------------

        voice_name = cls.get_voice_name(
            language=language,
            gender=gender,
        )

        logger.info(
            f"Synthesizing speech in '{language}' "
            f"using voice '{voice_name}'..."
        )

        try:
            communicate = edge_tts.Communicate(
                text,
                voice_name,
            )

            audio_stream = bytearray()

            async for chunk in communicate.stream():

                if chunk["type"] == "audio":
                    audio_stream.extend(
                        chunk["data"]
                    )

            if not audio_stream:
                raise RuntimeError(
                    "TTS returned empty audio."
                )

            return bytes(audio_stream)

        except Exception as exc:
            logger.error(
                "Neural TTS synthesis failed: "
                f"{exc}",
                exc_info=True,
            )

            raise RuntimeError(
                f"Speech synthesis failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Bhashini ASR Helper
    # ------------------------------------------------------------------

    @classmethod
    async def _bhashini_asr(
        cls,
        audio_bytes: bytes,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke Digital India Bhashini ULCA ASR.
        """

        headers = {
            "userID": settings.BHASHINI_USER_ID,
            "ulcaApiKey": settings.BHASHINI_API_KEY,
            "Content-Type": "application/json",
        }

        b64_audio = base64.b64encode(
            audio_bytes
        ).decode("utf-8")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {
                            "sourceLanguage": language,
                        },
                    },
                }
            ],
            "inputData": {
                "audio": [
                    {
                        "audioContent": b64_audio,
                    }
                ]
            },
        }

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.post(
                BHASHINI_ULCA_COMPUTE_URL,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Bhashini ASR returned "
                    f"HTTP {response.status_code}"
                )

            data = response.json()

            transcription = (
                data[
                    "pipelineResponse"
                ][0][
                    "output"
                ][0][
                    "source"
                ]
            )

            if not transcription:
                return None

            return {
                "text": transcription,
                "language": language,
                "engine": (
                    "Digital-India-Bhashini-ULCA"
                ),
            }

    # ------------------------------------------------------------------
    # Bhashini TTS Helper
    # ------------------------------------------------------------------

    @classmethod
    async def _bhashini_tts(
        cls,
        text: str,
        language: str,
        gender: str,
    ) -> Optional[bytes]:
        """
        Invoke Digital India Bhashini ULCA TTS.
        """

        headers = {
            "userID": settings.BHASHINI_USER_ID,
            "ulcaApiKey": settings.BHASHINI_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {
                            "sourceLanguage": language,
                        },
                        "gender": gender,
                    },
                }
            ],
            "inputData": {
                "input": [
                    {
                        "source": text,
                    }
                ]
            },
        }

        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.post(
                BHASHINI_ULCA_COMPUTE_URL,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Bhashini TTS returned "
                    f"HTTP {response.status_code}"
                )

            data = response.json()

            audio_b64 = (
                data[
                    "pipelineResponse"
                ][0][
                    "audio"
                ][0][
                    "audioContent"
                ]
            )

            if not audio_b64:
                return None

            return base64.b64decode(
                audio_b64
            )