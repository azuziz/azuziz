import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from scribe.providers import STTSpec
from scribe.transcript import Segment, Transcript


@dataclass
class STTResult:
    transcript: Transcript
    latency_s: float
    cost_usd: float | None  # None when the provider's per-minute price isn't configured


class STTClient(Protocol):
    spec: STTSpec

    def transcribe(
        self, audio: bytes, filename: str, mime_type: str, language_hint: str | None = None
    ) -> STTResult: ...


log = logging.getLogger(__name__)
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def post_with_retry(url: str, attempts: int = 3, backoff_s: float = 2.0, **kwargs: Any) -> httpx.Response:
    """POST with retries on network errors, rate limits and 5xx. Other responses are returned as-is."""
    for attempt in range(1, attempts + 1):
        try:
            resp = httpx.post(url, **kwargs)
        except httpx.TransportError as e:
            if attempt == attempts:
                raise
            log.warning("STT request failed (%s), retry %d/%d", e, attempt, attempts - 1)
        else:
            if resp.status_code not in RETRYABLE_STATUS or attempt == attempts:
                return resp
            log.warning("STT returned %d, retry %d/%d", resp.status_code, attempt, attempts - 1)
        time.sleep(backoff_s * attempt)
    raise AssertionError("unreachable")


def cost_for(spec: STTSpec, duration_s: float | None) -> float | None:
    if spec.price_per_minute is None or duration_s is None:
        return None
    return round(spec.price_per_minute * duration_s / 60, 6)


def words_to_segments(words: list[dict], max_gap_s: float = 1.5, max_words: int = 40) -> list[Segment]:
    """Groups word-level STT output into segments: a new segment starts on a speaker change, a long pause,
    or after `max_words` words. Each word is a dict with text, start, end and optional speaker."""
    segments: list[Segment] = []
    current: list[dict] = []

    def flush() -> None:
        if not current:
            return
        text = "".join(w["text"] for w in current).strip()
        if text:
            segments.append(
                Segment(
                    id=len(segments),
                    speaker=current[0].get("speaker"),
                    start=current[0].get("start"),
                    end=current[-1].get("end"),
                    text=text,
                )
            )
        current.clear()

    n_words = 0
    for w in words:
        if current:
            prev = current[-1]
            speaker_changed = w.get("speaker") != current[0].get("speaker") and w.get("is_word", True)
            gap = (w.get("start") or 0) - (prev.get("end") or 0)
            if speaker_changed or gap > max_gap_s or n_words >= max_words:
                flush()
                n_words = 0
        if not current and not w.get("is_word", True):
            continue  # don't start a segment with whitespace
        current.append(w)
        if w.get("is_word", True):
            n_words += 1
    flush()
    return segments
