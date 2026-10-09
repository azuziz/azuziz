import time
from dataclasses import dataclass

from scribe.providers import ProviderError, STTSpec
from scribe.stt.base import STTResult, cost_for, post_with_retry, words_to_segments
from scribe.transcript import Segment, Transcript


@dataclass
class ElevenLabsSTT:
    """ElevenLabs Scribe: POST {base_url}/speech-to-text, multipart, word timestamps and speaker diarization."""

    spec: STTSpec
    timeout_s: float = 600.0

    def transcribe(self, audio: bytes, filename: str, mime_type: str, language_hint: str | None = None) -> STTResult:
        data = {
            "model_id": self.spec.model or "scribe_v2",
            "diarize": "true",
            "timestamps_granularity": "word",
            "tag_audio_events": "false",
            **{k: str(v) for k, v in self.spec.params.items()},
        }
        # Consultations mix Uzbek and Russian, so by default we let the model detect the language.
        if language_hint:
            data["language_code"] = language_hint
        started = time.perf_counter()
        resp = post_with_retry(
            f"{self.spec.base_url}/speech-to-text",
            headers={"xi-api-key": self.spec.api_key()},
            data=data,
            files={"file": (filename, audio, mime_type)},
            timeout=self.timeout_s,
        )
        latency = time.perf_counter() - started
        if resp.status_code != 200:
            raise ProviderError(f"ElevenLabs STT failed ({resp.status_code}): {resp.text[:500]}")
        transcript = parse_response(resp.json())
        transcript.provider = self.spec.id
        return STTResult(transcript=transcript, latency_s=latency, cost_usd=cost_for(self.spec, transcript.duration_s))


def parse_response(body: dict) -> Transcript:
    words = [
        {
            "text": w.get("text", ""),
            "start": w.get("start"),
            "end": w.get("end"),
            "speaker": w.get("speaker_id"),
            "is_word": w.get("type", "word") == "word",
        }
        for w in body.get("words") or []
        if w.get("type", "word") in ("word", "spacing")
    ]
    segments = words_to_segments(words)
    if not segments and body.get("text"):
        segments = [Segment(id=0, text=body["text"])]
    ends = [w["end"] for w in words if w.get("end") is not None]
    return Transcript(segments=segments, language=body.get("language_code"), duration_s=max(ends) if ends else None)
