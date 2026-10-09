"""Offline stand-in for an LLM, so the app and the eval harness run without API keys.

It does no medical reasoning: it copies the first patient turn into Complaints and marks everything else as not
mentioned. The UI shows a "demo mode" banner whenever it is used.
"""

import json
import re
from dataclasses import dataclass

from scribe.llm.client import ChatResult, JsonSchemaFormat, Usage
from scribe.providers import LLMSpec

_LINE = re.compile(r"^\[(\d+)\]\s*(?:([^:\]]{1,30}):\s*)?(.*)$")
_DOCTOR_LABELS = {"doctor", "shifokor", "врач", "speaker_0"}


@dataclass
class FakeChatClient:
    spec: LLMSpec

    def chat(self, messages: list[dict[str, str]], fmt: JsonSchemaFormat) -> ChatResult:
        if fmt.name != "clinical_note":
            raise ValueError(f"FakeChatClient cannot produce '{fmt.name}'")
        user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        segments = []
        for line in user.splitlines():
            m = _LINE.match(line.strip())
            if m:
                segments.append((int(m.group(1)), (m.group(2) or "").strip().lower(), m.group(3).strip()))
        patient_turn = next(((i, t) for i, spk, t in segments if spk not in _DOCTOR_LABELS), None)
        note = {
            "complaints": {"text": patient_turn[1], "evidence": [patient_turn[0]]}
            if patient_turn
            else {"text": "", "evidence": []},
            "not_mentioned": [
                "history_present_illness",
                "history_life",
                "allergies",
                "objective",
                "diagnoses",
                "workup_plan",
                "medications",
                "recommendations",
                "follow_up",
            ],
        }
        content = json.dumps(note, ensure_ascii=False)
        return ChatResult(
            content=content,
            usage=Usage(input_tokens=len(user) // 4, output_tokens=len(content) // 4, latency_s=0.0, calls=1),
            structured_output_used="fake",
        )
