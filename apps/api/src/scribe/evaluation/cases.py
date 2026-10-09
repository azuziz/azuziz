import json
from dataclasses import dataclass, field
from pathlib import Path

from scribe.transcript import Segment, Transcript

AUDIO_SUFFIXES = (".webm", ".m4a", ".mp4", ".mp3", ".wav", ".ogg", ".flac")


@dataclass
class Fact:
    id: str
    fact: str
    critical: bool = False
    keywords: list[str] = field(default_factory=list)


@dataclass
class EvalCase:
    id: str
    title: str
    specialty: str
    conversation_language: str
    output_language: str
    segments: list[dict]
    facts: list[Fact]
    expected_icd10: list[str] = field(default_factory=list)
    acceptable_icd10: list[str] = field(default_factory=list)
    medical_terms: list[str] = field(default_factory=list)
    synthetic: bool = False
    review_status: str = ""
    audio_path: Path | None = None

    def transcript(self) -> Transcript:
        return Transcript(
            segments=[Segment(id=i, speaker=s.get("speaker"), text=s["text"]) for i, s in enumerate(self.segments)]
        )

    @property
    def reference_text(self) -> str:
        return " ".join(s["text"] for s in self.segments)


def load_case(case_dir: Path) -> EvalCase:
    data = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    facts = [Fact(**f) for f in data.pop("facts")]
    audio = next((p for p in sorted(case_dir.iterdir()) if p.suffix.lower() in AUDIO_SUFFIXES), None)
    return EvalCase(facts=facts, audio_path=audio, **data)


def load_cases(root: Path, only: list[str] | None = None) -> list[EvalCase]:
    cases = [load_case(d) for d in sorted(root.iterdir()) if (d / "case.json").exists()]
    if only:
        cases = [c for c in cases if c.id in only]
    return cases
