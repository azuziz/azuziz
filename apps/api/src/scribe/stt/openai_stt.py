import time
from dataclasses import dataclass

from scribe.providers import ProviderError, STTSpec
from scribe.stt.base import STTResult, cost_for, post_with_retry
from scribe.transcript import Segment, Transcript


@dataclass
class OpenAICompatibleSTT:
    """POST {base_url}/audio/transcriptions. Works with OpenAI and other hosts of Whisper-style models.

    `verbose_json` returns timed segments where the model supports it; otherwise we get one untimed segment.
    """

    spec: STTSpec
    timeout_s: float = 600.0

    def transcribe(self, audio: bytes, filename: str, mime_type: str, language_hint: str | None = None) -> STTResult:
        data = {
            "model": self.spec.model or "whisper-1",
            "response_format": self.spec.params.get("response_format", "json"),
        }
        if language_hint:
            data["language"] = language_hint
        started = time.perf_counter()
        resp = post_with_retry(
            f"{self.spec.base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.spec.api_key()}"},
            data=data,
            files={"file": (filename, audio, mime_type)},
            timeout=self.timeout_s,
        )
        latency = time.perf_counter() - started
        if resp.status_code != 200:
            raise ProviderError(f"Transcription failed ({resp.status_code}): {resp.text[:500]}")
        transcript = parse_response(resp.json())
        transcript.provider = self.spec.id
        return STTResult(transcript=transcript, latency_s=latency, cost_usd=cost_for(self.spec, transcript.duration_s))


def parse_response(body: dict) -> Transcript:
    raw_segments = body.get("segments") or []
    if raw_segments:
        segments = [
            Segment(id=i, start=s.get("start"), end=s.get("end"), text=s.get("text", "").strip())
            for i, s in enumerate(raw_segments)
            if s.get("text", "").strip()
        ]
    else:
        segments = [Segment(id=0, text=body.get("text", "").strip())]
    return Transcript(segments=segments, language=body.get("language"), duration_s=body.get("duration"))
