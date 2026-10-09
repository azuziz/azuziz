"""Structured outpatient note in the post-Soviet / Uzbek MoH layout.

Every item cites `evidence`: the ids of transcript segments it came from. Nothing is invented: a section that was
not discussed stays empty and its key goes into `not_mentioned`.
"""

import copy
from typing import Any, Literal

from pydantic import BaseModel, Field

OutputLanguage = Literal["uz-Latn", "uz-Cyrl", "ru"]
OUTPUT_LANGUAGES: tuple[str, ...] = ("uz-Latn", "uz-Cyrl", "ru")


class Section(BaseModel):
    text: str = ""
    evidence: list[int] = Field(default_factory=list)


class Vitals(BaseModel):
    blood_pressure: str | None = None  # "165/100"
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    temperature_c: float | None = None
    spo2: int | None = None
    weight_kg: float | None = None
    height_cm: float | None = None


class Objective(Section):
    vitals: Vitals = Field(default_factory=Vitals)


class Allergy(BaseModel):
    substance: str
    reaction: str | None = None
    evidence: list[int] = Field(default_factory=list)


class Diagnosis(BaseModel):
    text: str
    icd10: str | None = None
    kind: Literal["main", "secondary", "complication"] = "main"
    evidence: list[int] = Field(default_factory=list)


class Medication(BaseModel):
    drug: str
    dose: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None
    evidence: list[int] = Field(default_factory=list)


class PlanItem(BaseModel):
    text: str
    evidence: list[int] = Field(default_factory=list)


class Note(BaseModel):
    complaints: Section = Field(default_factory=Section)
    history_present_illness: Section = Field(default_factory=Section)
    history_life: Section = Field(default_factory=Section)
    allergies: list[Allergy] = Field(default_factory=list)
    allergies_denied: bool = False  # true only if the patient explicitly said they have no allergies
    objective: Objective = Field(default_factory=Objective)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    workup_plan: list[PlanItem] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    recommendations: Section = Field(default_factory=Section)
    follow_up: Section = Field(default_factory=Section)
    not_mentioned: list[str] = Field(default_factory=list)

    def evidence_ids(self) -> list[int]:
        ids: list[int] = []
        for sec in (
            self.complaints,
            self.history_present_illness,
            self.history_life,
            self.objective,
            self.recommendations,
            self.follow_up,
        ):
            ids += sec.evidence
        for items in (self.allergies, self.diagnoses, self.workup_plan, self.medications):
            for item in items:
                ids += item.evidence
        return ids

    def drop_unknown_evidence(self, valid_ids: set[int]) -> int:
        """Removes evidence ids that don't exist in the transcript. Returns how many were removed."""
        removed = 0

        def clean(obj: Any) -> None:
            nonlocal removed
            kept = [i for i in obj.evidence if i in valid_ids]
            removed += len(obj.evidence) - len(kept)
            obj.evidence = kept

        for sec in (
            self.complaints,
            self.history_present_illness,
            self.history_life,
            self.objective,
            self.recommendations,
            self.follow_up,
        ):
            clean(sec)
        for items in (self.allergies, self.diagnoses, self.workup_plan, self.medications):
            for item in items:
                clean(item)
        return removed


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON schema accepted by strict structured-output modes: every property required, no extra properties.

    Optional fields stay nullable (`anyOf [..., null]`), so "required" only means the key must be present.
    """
    schema = copy.deepcopy(model.model_json_schema())

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            node.pop("title", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    return schema


# ---------------------------------------------------------------- rendering

HEADINGS: dict[str, dict[str, str]] = {
    "uz-Latn": {
        "complaints": "Shikoyatlar",
        "history_present_illness": "Kasallik anamnezi",
        "history_life": "Hayot anamnezi",
        "allergies": "Allergologik anamnez",
        "objective": "Obʼektiv holat",
        "diagnoses": "Tashxis",
        "workup_plan": "Tekshiruv rejasi",
        "medications": "Davolash",
        "recommendations": "Tavsiyalar",
        "follow_up": "Nazorat",
        "no_allergies": "Allergiya inkor etiladi",
        "bp": "AQB",
        "hr": "YuUS",
        "rr": "NOS",
        "temp": "Tana harorati",
        "weight": "Vazn",
        "height": "Boʻy",
    },
    "uz-Cyrl": {
        "complaints": "Шикоятлар",
        "history_present_illness": "Касаллик анамнези",
        "history_life": "Ҳаёт анамнези",
        "allergies": "Аллергологик анамнез",
        "objective": "Объектив ҳолат",
        "diagnoses": "Ташхис",
        "workup_plan": "Текширув режаси",
        "medications": "Даволаш",
        "recommendations": "Тавсиялар",
        "follow_up": "Назорат",
        "no_allergies": "Аллергия инкор этилади",
        "bp": "АҚБ",
        "hr": "ЮУС",
        "rr": "НОС",
        "temp": "Тана ҳарорати",
        "weight": "Вазн",
        "height": "Бўй",
    },
    "ru": {
        "complaints": "Жалобы",
        "history_present_illness": "Анамнез заболевания",
        "history_life": "Анамнез жизни",
        "allergies": "Аллергоанамнез",
        "objective": "Объективный статус",
        "diagnoses": "Диагноз",
        "workup_plan": "План обследования",
        "medications": "Лечение",
        "recommendations": "Рекомендации",
        "follow_up": "Явка",
        "no_allergies": "Аллергию отрицает",
        "bp": "АД",
        "hr": "ЧСС",
        "rr": "ЧДД",
        "temp": "Температура",
        "weight": "Вес",
        "height": "Рост",
    },
}


def _vitals_line(v: Vitals, h: dict[str, str]) -> str:
    parts = []
    if v.blood_pressure:
        parts.append(f"{h['bp']} {v.blood_pressure}")
    if v.heart_rate is not None:
        parts.append(f"{h['hr']} {v.heart_rate}")
    if v.respiratory_rate is not None:
        parts.append(f"{h['rr']} {v.respiratory_rate}")
    if v.temperature_c is not None:
        parts.append(f"{h['temp']} {v.temperature_c} °C")
    if v.spo2 is not None:
        parts.append(f"SpO₂ {v.spo2}%")
    if v.weight_kg is not None:
        parts.append(f"{h['weight']} {v.weight_kg:g} kg")
    if v.height_cm is not None:
        parts.append(f"{h['height']} {v.height_cm:g} cm")
    return ", ".join(parts)


def render_sections(note: Note, language: str) -> list[dict[str, Any]]:
    """The note's non-empty sections in display order: key, localized heading, body text and evidence ids."""
    h = HEADINGS.get(language, HEADINGS["ru"])
    sections: list[dict[str, Any]] = []

    def add(key: str, body: str, evidence: list[int]) -> None:
        if body.strip():
            sections.append({"key": key, "heading": h[key], "body": body.strip(), "evidence": sorted(set(evidence))})

    def items_evidence(items: list[Any]) -> list[int]:
        return [i for item in items for i in item.evidence]

    add("complaints", note.complaints.text, note.complaints.evidence)
    add("history_present_illness", note.history_present_illness.text, note.history_present_illness.evidence)
    add("history_life", note.history_life.text, note.history_life.evidence)
    if note.allergies:
        body = "\n".join(f"- {a.substance}" + (f" ({a.reaction})" if a.reaction else "") for a in note.allergies)
        add("allergies", body, items_evidence(note.allergies))
    elif note.allergies_denied:
        add("allergies", h["no_allergies"], [])
    objective = "\n".join(x for x in (_vitals_line(note.objective.vitals, h), note.objective.text) if x)
    add("objective", objective, note.objective.evidence)
    add(
        "diagnoses",
        "\n".join(f"- {d.text}" + (f" ({d.icd10})" if d.icd10 else "") for d in note.diagnoses),
        items_evidence(note.diagnoses),
    )
    add("workup_plan", "\n".join(f"- {p.text}" for p in note.workup_plan), items_evidence(note.workup_plan))
    add(
        "medications",
        "\n".join(f"- {medication_line(m)}" for m in note.medications),
        items_evidence(note.medications),
    )
    add("recommendations", note.recommendations.text, note.recommendations.evidence)
    add("follow_up", note.follow_up.text, note.follow_up.evidence)
    return sections


def render_text(note: Note, language: str) -> str:
    """Plain-text note for copy-paste into an EHR, with headings in the note's language."""
    return "\n\n".join(f"{s['heading']}:\n{s['body']}" for s in render_sections(note, language))


def medication_line(m: Medication) -> str:
    details = ", ".join(x for x in (m.dose, m.route, m.frequency, m.duration, m.instructions) if x)
    return f"{m.drug} — {details}" if details else m.drug
