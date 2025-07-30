from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import whisperx  # type: ignore
from app.settings import settings

from importlib.metadata import version
import faster_whisper, ctranslate2
print("[versions]", "whisperx", version("whisperx"), "faster_whisper", faster_whisper.__version__, "ctranslate2", ctranslate2.__version__)


# Simple single-process caches
_asr_model = None
_align_model = None
_align_metadata = None
_diarizer = None

def _load_asr():
    global _asr_model
    if _asr_model is None:
        print(f"[whisperx] Loading ASR model={settings.WHISPERX_MODEL_NAME} device={settings.WHISPERX_DEVICE} compute_type={settings.WHISPERX_COMPUTE_TYPE}")
        _asr_model = whisperx.load_model(
            settings.WHISPERX_MODEL_NAME,
            device=settings.WHISPERX_DEVICE,
            compute_type=settings.WHISPERX_COMPUTE_TYPE,
        )
    return _asr_model

def _load_alignment(language_code: str):
    global _align_model, _align_metadata
    if _align_model is None or _align_metadata is None:
        _align_model, _align_metadata = whisperx.load_align_model(
            language_code=language_code, device=settings.WHISPERX_DEVICE
        )
    return _align_model, _align_metadata

def _load_diarizer():
    global _diarizer
    if _diarizer is None:
        # Requires a HuggingFace token in many cases to pull pyannote models
        _diarizer = whisperx.DiarizationPipeline(
            use_auth_token=settings.HUGGINGFACE_TOKEN, device=settings.WHISPERX_DEVICE
        )
    return _diarizer

def transcribe_with_whisperx(audio_path: str) -> Dict[str, Any]:
    # 1) Load audio
    audio = whisperx.load_audio(audio_path)

    # 2) ASR
    asr = _load_asr()
    # You can tweak batch_size; lower values reduce memory
    asr_result = asr.transcribe(audio, batch_size=8)
    # asr_result keys: "segments" (list of dicts), "text", "language", etc.

    language = asr_result.get("language", None)

    # 3) Optional alignment (word timestamps)
    aligned = asr_result
    if settings.WHISPERX_ENABLE_ALIGNMENT and language:
        try:
            align_model, align_meta = _load_alignment(language_code=language)
            aligned = whisperx.align(
                asr_result["segments"], align_model, align_meta, audio, settings.WHISPERX_DEVICE,
                return_char_alignments=False,
            )
        except Exception as e:
            # Fall back gracefully if alignment model fails
            aligned = asr_result

    # 4) Optional diarization
    diar_segments = None
    if settings.WHISPERX_ENABLE_DIARIZATION:
        try:
            diarizer = _load_diarizer()
            diar_segments = diarizer(audio)
            aligned = whisperx.assign_word_speakers(diar_segments, aligned)
        except Exception:
            # Ignore diarization errors for MVP
            pass

    # 5) Convert to our contract
    out_segments: List[Dict[str, Any]] = []
    for seg in aligned.get("segments", []):
        words = []
        for w in seg.get("words", []) or []:
            words.append({
                "word": w.get("word"),
                "start": float(w["start"]) if w.get("start") is not None else None,
                "end": float(w["end"]) if w.get("end") is not None else None,
                "confidence": float(w["score"]) if w.get("score") is not None else None,
            })
        out_segments.append({
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": seg.get("text", ""),
            "words": words,
            "speaker": seg.get("speaker")  # will be present if diarization ran
        })

    return {
        "language": language,
        "duration_sec": float(aligned.get("duration", 0.0)) if "duration" in aligned else None,
        "segments": out_segments,
        "model": {
            "name": f"whisperx-{settings.WHISPERX_MODEL_NAME}",
            "device": settings.WHISPERX_DEVICE,
            "compute_type": settings.WHISPERX_COMPUTE_TYPE,
            "alignment": bool(settings.WHISPERX_ENABLE_ALIGNMENT),
            "diarization": bool(settings.WHISPERX_ENABLE_DIARIZATION),
        }
    }
