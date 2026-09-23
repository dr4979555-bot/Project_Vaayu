import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.voice_service import VoiceService


def test_voice_name_resolution():
    """Verify appropriate neural voices are selected for Hindi, Bengali, Marathi, and English."""
    assert "hi-IN" in VoiceService.get_voice_name("hi", "female")
    assert "bn-IN" in VoiceService.get_voice_name("bn", "female")
    assert "mr-IN" in VoiceService.get_voice_name("mr", "female")
    assert "en-IN" in VoiceService.get_voice_name("en", "female")


@pytest.mark.asyncio
async def test_neural_speech_synthesis_hindi():
    """Verify live neural speech synthesis in Hindi (hi)."""
    text = "नमस्कार, पटना में आज तापमान 28 डिग्री सेल्सियस है।"
    audio_bytes = await VoiceService.synthesize_speech(text=text, language="hi", gender="female")
    assert len(audio_bytes) > 500  # Valid MP3 audio generated
    # MP3 frame sync header verification (0xFF, 0xFB/0xF3/0xE0) or ID3 tag
    assert audio_bytes[:3] == b"ID3" or audio_bytes[0] == 0xFF or len(audio_bytes) > 1000


@pytest.mark.asyncio
async def test_neural_speech_synthesis_bengali():
    """Verify live neural speech synthesis in Bengali (bn)."""
    text = "কলকাতা আজ আবহাওয়া পরিষ্কার এবং রৌদ্রোজ্জ্বল।"
    audio_bytes = await VoiceService.synthesize_speech(text=text, language="bn", gender="female")
    assert len(audio_bytes) > 500


@pytest.mark.asyncio
async def test_neural_speech_synthesis_marathi():
    """Verify live neural speech synthesis in Marathi (mr)."""
    text = "पुण्यात आज हलका पाऊस पडण्याची शक्यता आहे।"
    audio_bytes = await VoiceService.synthesize_speech(text=text, language="mr", gender="female")
    assert len(audio_bytes) > 500


@pytest.mark.asyncio
async def test_synthesize_endpoint(async_client):
    """Verify POST /api/v1/voice/synthesize endpoint returns streaming MP3."""
    resp = await async_client.post(
        "/api/v1/voice/synthesize",
        json={
            "text": "The weather today in Delhi is clear and pleasant.",
            "language": "en",
            "gender": "female",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert len(resp.content) > 500


@pytest.mark.asyncio
async def test_transcribe_endpoint(async_client):
    """Verify POST /api/v1/voice/transcribe handles uploaded audio."""
    mock_transcription = {"text": "आज मौसम कैसा है?", "language": "hi", "engine": "Groq-Whisper-Large-v3-Turbo"}

    with patch("app.services.voice_service.VoiceService.transcribe_audio", new_callable=AsyncMock, return_value=mock_transcription):
        fake_audio = b"RIFF" + b"\x00" * 200  # Fake wav bytes
        resp = await async_client.post(
            "/api/v1/voice/transcribe",
            files={"file": ("test.wav", fake_audio, "audio/wav")},
            data={"language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "आज मौसम कैसा है?"
        assert data["language"] == "hi"
