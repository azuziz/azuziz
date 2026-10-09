from pydantic import BaseModel


class Segment(BaseModel):
    id: int
    speaker: str | None = None  # e.g. "doctor", "patient", or a raw diarization label like "speaker_0"
    start: float | None = None  # seconds
    end: float | None = None
    text: str


class Transcript(BaseModel):
    segments: list[Segment]
    language: str | None = None  # detected language code, if the STT reports one
    duration_s: float | None = None
    provider: str | None = None

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    def for_prompt(self) -> str:
        """Numbered lines the LLM cites as evidence, e.g. `[3] patient: ...`."""
        lines = []
        for s in self.segments:
            speaker = f"{s.speaker}: " if s.speaker else ""
            lines.append(f"[{s.id}] {speaker}{s.text.strip()}")
        return "\n".join(lines)

    @property
    def segment_ids(self) -> set[int]:
        return {s.id for s in self.segments}
