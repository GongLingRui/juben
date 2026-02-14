import os
import tempfile
from typing import Dict, Any, Optional

from config.settings import JubenSettings


class ASRService:
    def __init__(self):
        self.settings = JubenSettings()
        self.provider = self.settings.asr.provider
        self.model_name = self.settings.asr.model
        self.device = self._resolve_device(self.settings.asr.device)
        self.compute_type = self.settings.asr.compute_type
        self.download_root = self.settings.asr.download_root
        self.default_language = self.settings.asr.language
        self._model_cache: Dict[str, Any] = {}

    def _resolve_device(self, device: str) -> str:
        if device and device != "auto":
            return device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _get_model(self, model_name: Optional[str] = None):
        name = model_name or self.model_name
        if name in self._model_cache:
            return self._model_cache[name]
        from faster_whisper import WhisperModel
        model = WhisperModel(
            name,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.download_root
        )
        self._model_cache[name] = model
        return model

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None, model: Optional[str] = None, file_suffix: str = ".wav") -> Dict[str, Any]:
        if self.provider != "local_whisper":
            raise ValueError(f"ASR provider not supported: {self.provider}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix or ".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            whisper_model = self._get_model(model)
            segments, info = whisper_model.transcribe(
                tmp_path,
                language=language or self.default_language,
                vad_filter=True
            )
            text = "".join([seg.text for seg in segments]).strip()
            return {
                "text": text,
                "language": info.language,
                "duration": info.duration,
                "model": model or self.model_name,
                "device": self.device
            }
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
