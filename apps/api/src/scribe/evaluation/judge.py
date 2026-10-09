"""Grades a generated note against the transcript and the case's key facts."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from scribe.evaluation.cases import EvalCase
from scribe.evaluation.text import keywords_found
from scribe.llm.client import ChatClient, JsonSchemaFormat, Usage, parse_json
from scribe.notes.schema import HEADINGS, Note, medication_line, strict_json_schema


class FactVerdict(BaseModel):
    id: str
    status: Literal["captured", "partial", "missing", "wrong"]
    comment: str


class UnsupportedStatement(BaseModel):
    statement: str
    severity: Literal["critical", "major", "minor"]
    reason: str


class JudgeVerdict(BaseModel):
    facts: list[FactVerdict]
    unsupported: list[UnsupportedStatement]


JUDGE_FORMAT = JsonSchemaFormat(name="judge_verdict", schema=strict_json_schema(JudgeVerdict))

JUDGE_SYSTEM = """You audit AI-generated clinical notes for a medical scribe used in Uzbekistan. The consultation \
may be in Uzbek, Russian or both; the note may be in Uzbek (Latin or Cyrillic) or Russian. Judge meaning, not wording.

1. For each key fact, decide:
   - "captured": present and every clinically relevant detail is correct (values, doses, units, frequency, duration)
   - "partial": present but missing some detail
   - "missing": absent
   - "wrong": present but with an incorrect detail (e.g. a wrong dose, or a value that was later corrected)
2. List every statement in the note that the transcript does not support or that contradicts it. Severity:
   - "critical": a wrong or invented drug, dose, frequency, route, allergy or diagnosis
   - "major": an invented or wrong finding, vital sign, lab value, history item or plan item
   - "minor": a harmless overstatement or inference
   Do not list statements that are supported, even if paraphrased or translated.

Return only the JSON object."""


@dataclass
class Grade:
    facts: dict[str, str]  # fact id -> status
    unsupported: list[dict]
    usage: Usage
    judge: str  # model id, or "keywords"

    def recall(self) -> float:
        if not self.facts:
            return 0.0
        score = {"captured": 1.0, "partial": 0.5}
        return sum(score.get(s, 0.0) for s in self.facts.values()) / len(self.facts)

    def count(self, severity: str) -> int:
        return sum(1 for u in self.unsupported if u["severity"] == severity)

    def critical_errors(self, case: EvalCase) -> int:
        """Critical hallucinations plus critical facts recorded wrongly (e.g. the pre-correction dose)."""
        critical_ids = {f.id for f in case.facts if f.critical}
        wrong_critical = sum(1 for fid, s in self.facts.items() if fid in critical_ids and s == "wrong")
        return self.count("critical") + wrong_critical

    def critical_omissions(self, case: EvalCase) -> int:
        critical_ids = {f.id for f in case.facts if f.critical}
        return sum(1 for fid, s in self.facts.items() if fid in critical_ids and s == "missing")


def note_content(note: Note, language: str) -> str:
    """All the note's content without section headings, for keyword matching."""
    parts = [
        note.complaints.text,
        note.history_present_illness.text,
        note.history_life.text,
        note.objective.text,
        note.recommendations.text,
        note.follow_up.text,
    ]
    v = note.objective.vitals
    parts += [str(x) for x in (v.blood_pressure, v.heart_rate, v.respiratory_rate, v.temperature_c, v.spo2) if x]
    parts += [str(x) for x in (v.weight_kg, v.height_cm) if x]
    parts += [f"{a.substance} {a.reaction or ''}" for a in note.allergies]
    if note.allergies_denied:
        parts.append(HEADINGS.get(language, HEADINGS["ru"])["no_allergies"])
    parts += [f"{d.text} {d.icd10 or ''}" for d in note.diagnoses]
    parts += [p.text for p in note.workup_plan]
    parts += [medication_line(m) for m in note.medications]
    return "\n".join(p for p in parts if p)


def keyword_grade(case: EvalCase, note: Note) -> Grade:
    """Cheap, deterministic grading from the facts' keywords. It can't detect hallucinations."""
    content = note_content(note, case.output_language)
    facts = {
        f.id: ("captured" if f.keywords and keywords_found(f.keywords, content) else "missing") for f in case.facts
    }
    return Grade(facts=facts, unsupported=[], usage=Usage(), judge="keywords")


def llm_grade(client: ChatClient, case: EvalCase, note_text: str) -> Grade:
    facts = "\n".join(f"- {f.id}{' (critical)' if f.critical else ''}: {f.fact}" for f in case.facts)
    user = (
        f"Transcript:\n{case.transcript().for_prompt()}\n\n"
        f"Key facts:\n{facts}\n\n"
        f"Note ({case.output_language}):\n{note_text}"
    )
    messages = [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}]
    result = client.chat(messages, JUDGE_FORMAT)
    verdict = JudgeVerdict.model_validate(parse_json(result.content))
    statuses = {v.id: v.status for v in verdict.facts}
    # A fact the judge forgot to mention counts as missing.
    facts_map = {f.id: statuses.get(f.id, "missing") for f in case.facts}
    return Grade(
        facts=facts_map,
        unsupported=[u.model_dump() for u in verdict.unsupported],
        usage=result.usage,
        judge=client.spec.id,
    )
