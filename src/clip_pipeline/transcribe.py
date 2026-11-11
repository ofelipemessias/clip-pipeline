"""Transcricao local com faster-whisper."""
from faster_whisper import WhisperModel

from .models import Segment


def transcribe(video_path: str, model_size: str = "tiny", language: str | None = None) -> list[Segment]:
    """Transcreve o audio do video e retorna segmentos com tempos.

    O modelo whisper e baixado na primeira execucao (cache do faster-whisper).
    """
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(video_path, language=language, vad_filter=True)
    return [Segment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]
