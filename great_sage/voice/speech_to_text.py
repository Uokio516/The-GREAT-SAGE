"""
Local speech-to-text via faster-whisper - CPU-only, fully offline, no
cloud API. Used by both push-to-talk and the wake-word listener (see
speech_input.py) to turn recorded microphone audio into text, which then
feeds into the same ChatEngine path a typed message would.

The model loads lazily (first call only) and stays cached for the life of
the process - loading takes a couple seconds, so it happens once, not per
utterance. First run also downloads the model (~145MB for "base.en") to
the Hugging Face cache.
"""

import logging

import numpy as np

from great_sage.config import settings
from great_sage.zh import to_tw

log = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # 繁中化：原本是只認英文的 base.en。改成多語模型（預設 small，約
        # 460MB），中文辨識率比 base 好很多，CPU int8 跑短句仍在一兩秒內。
        # 顯存留給語音合成和 LLM，所以維持在 CPU。
        # 先用本機已下載的模型，不上網檢查新版本。原本每次載入都會先連
        # Hugging Face，網路一斷（或連線被重設）語音辨識就整個失敗，
        # 即使模型早就在電腦裡。只有本機沒有時才下載。
        try:
            _model = WhisperModel(settings.STT_MODEL, device="cpu",
                                  compute_type="int8", local_files_only=True)
        except Exception:
            log.info("Whisper %s not cached locally - downloading", settings.STT_MODEL)
            _model = WhisperModel(settings.STT_MODEL, device="cpu",
                                  compute_type="int8")
    return _model


def transcribe(audio: np.ndarray) -> str:
    """audio must be mono float32 samples at 16000 Hz (speech_input.py's
    recorders capture at that rate directly, so no resampling needed)."""
    if audio.size == 0:
        log.warning("Transcription skipped: empty recording")
        return ""
    model = _get_model()
    segments, _ = model.transcribe(
        audio, language=settings.STT_LANGUAGE, vad_filter=True,
        # 用繁體的提示句把 Whisper 往繁體拉；漏掉的簡體再由 to_tw 補轉。
        initial_prompt=settings.STT_INITIAL_PROMPT or None)
    text = to_tw("".join(seg.text for seg in segments).strip())

    # An empty result used to be completely silent: faster_whisper logged
    # that it processed the audio, this returned "", and the caller simply
    # did nothing. Push-to-talk looked like it worked while Sage never
    # heard a word, with nothing anywhere saying why.
    #
    # That is exactly how a packaged build failed - vad_filter needs
    # faster_whisper's assets/silero_vad_v6.onnx, which was not bundled,
    # so nothing was ever detected as speech. Worth a line in the log
    # whichever way it goes.
    seconds = audio.size / 16000.0
    if text:
        log.info("Transcribed %.1fs of audio: %r", seconds, text)
    else:
        log.warning(
            "Transcribed %.1fs of audio but got NO text. Either nothing was "
            "said, or the VAD filter rejected it - check that "
            "faster_whisper/assets/silero_vad_v6.onnx is present.", seconds)
    return text
