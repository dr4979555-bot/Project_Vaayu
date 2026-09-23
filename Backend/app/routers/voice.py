import base64
import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.limiter import limiter
from app.services.voice_service import VoiceService
from app.services.agent_service import WeatherAgent

logger = logging.getLogger("WeatherGPT.VoiceRouter")
router = APIRouter()


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to synthesize into speech")
    language: str = Field("hi", description="Language code: hi | bn | mr | en")
    gender: str = Field("female", description="Voice gender: female | male")


class VoiceChatResponse(BaseModel):
    transcription: str
    response_text: str
    language: str
    ground_truth: dict
    audio_base64: str


# ---------------------------------------------------------------------------
# POST /transcribe — Speech-to-Text (ASR)
# ---------------------------------------------------------------------------
@router.post(
    "/transcribe",
    summary="Speech-to-Text (ASR) for Hindi, Bengali, Marathi, and English",
)
@limiter.limit("30/minute")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, WEBM)"),
    language: Optional[str] = Form(None, description="Expected ISO language code (e.g. hi, bn, mr, en)"),
):
    """
    Transcribes an uploaded voice audio file to natural language text.
    Supports Bhashini ULCA ASR and Groq Whisper Large v3 Turbo.
    """
    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty or corrupted.",
        )

    try:
        result = await VoiceService.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language,
        )
        return result
    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech transcription failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# POST /synthesize — Text-to-Speech (TTS)
# ---------------------------------------------------------------------------
@router.post(
    "/synthesize",
    summary="Text-to-Speech (TTS) for Hindi, Bengali, Marathi, and English",
)
@limiter.limit("30/minute")
async def synthesize_speech(
    request: Request,
    payload: SynthesizeRequest,
):
    """
    Synthesizes natural language text into high-fidelity neural audio (MP3).
    Supports Hindi, Bengali, Marathi, and English.
    """
    try:
        audio_bytes = await VoiceService.synthesize_speech(
            text=payload.text,
            language=payload.language,
            gender=payload.gender,
        )
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="speech_{payload.language}.mp3"',
            },
        )
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}",
        )


# ---------------------------------------------------------------------------
# POST /chat — End-to-End Voice-to-Voice Conversational Loop
# ---------------------------------------------------------------------------
@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    summary="End-to-end voice-to-voice weather conversation",
)
@limiter.limit("20/minute")
async def voice_chat(
    request: Request,
    file: UploadFile = File(..., description="Voice query audio file"),
    latitude: float = Form(..., description="GPS latitude"),
    longitude: float = Form(..., description="GPS longitude"),
    language: str = Form("hi", description="Target language (hi, bn, mr, en)"),
    gender: str = Form("female", description="Voice gender (female, male)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Full voice conversational loop:
    1. Transcribes voice question (ASR)
    2. Retrieves real-time ground-truth weather for GPS coordinates
    3. Generates zero-hallucination meteorological advisory
    4. Synthesizes advisory to high-fidelity audio (TTS) in target language
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty voice audio submitted.",
        )

    # 1. ASR
    asr_res = await VoiceService.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=file.filename or "voice_query.wav",
        language=language,
    )
    user_query = asr_res["text"]

    # 2. Zero-Hallucination Weather Processing
    chat_response = await WeatherAgent.process_query(
        db=db,
        query=user_query,
        latitude=latitude,
        longitude=longitude,
        language=language,
    )

    # 3. TTS Synthesis
    audio_output = await VoiceService.synthesize_speech(
        text=chat_response.response,
        language=language,
        gender=gender,
    )
    audio_b64 = base64.b64encode(audio_output).decode("utf-8")

    return VoiceChatResponse(
        transcription=user_query,
        response_text=chat_response.response,
        language=language,
        ground_truth=chat_response.ground_truth,
        audio_base64=audio_b64,
    )
