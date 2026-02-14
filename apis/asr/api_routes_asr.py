from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from pathlib import Path

from utils.asr_service import ASRService

router = APIRouter(prefix="/juben/asr", tags=["ASR"])

asr_service = ASRService()


class ASRResponse(BaseModel):
    success: bool
    data: dict | None = None
    message: str | None = None


@router.post("/transcribe", response_model=ASRResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
    model: str | None = Form(default=None)
):
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="空音频文件")
        suffix = Path(audio.filename or "").suffix or ".wav"
        result = await asr_service.transcribe(audio_bytes, language=language, model=model, file_suffix=suffix)
        return ASRResponse(success=True, data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=ASRResponse)
async def asr_health():
    return ASRResponse(success=True, data={
        "provider": asr_service.provider,
        "model": asr_service.model_name,
        "device": asr_service.device,
        "compute_type": asr_service.compute_type
    })
