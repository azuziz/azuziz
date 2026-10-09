import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from scribe.config import API_ROOT, Settings
from scribe.llm.client import ChatResult, JsonSchemaFormat, Usage
from scribe.main import create_app
from scribe.providers import LLMSpec, load_registry
from scribe.transcript import Segment, Transcript


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "audio",
        audio_encryption_key=Fernet.generate_key().decode(),
        providers_file=API_ROOT / "providers.toml",
        stt_provider="fake",
        llm_model="fake",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, load_registry(settings.providers_file)))


@pytest.fixture
def transcript() -> Transcript:
    return Transcript(
        segments=[
            Segment(id=0, speaker="doctor", text="Nima bezovta qilyapti?"),
            Segment(id=1, speaker="patient", text="Boshim og'riyapti."),
            Segment(id=2, speaker="doctor", text="Amlodipin 10 milligramm kuniga bir marta."),
        ]
    )


@dataclass
class ScriptedClient:
    """Returns pre-set replies in order, and records the messages it was sent."""

    replies: list[str]
    spec: LLMSpec = field(
        default_factory=lambda: LLMSpec(
            id="scripted", label="Scripted", model="m", price_input=1.0, price_output=2.0, price_cached_input=0.1
        )
    )
    calls: list[list[dict]] = field(default_factory=list)

    def chat(self, messages: list[dict[str, str]], fmt: JsonSchemaFormat) -> ChatResult:
        self.calls.append(messages)
        return ChatResult(
            content=self.replies[len(self.calls) - 1],
            usage=Usage(input_tokens=1000, cached_input_tokens=200, output_tokens=500, latency_s=1.5, calls=1),
            structured_output_used="json_schema",
        )


VALID_NOTE = json.dumps(
    {
        "complaints": {"text": "Bosh ogʻrigʻi", "evidence": [1]},
        "medications": [
            {
                "drug": "amlodipin",
                "dose": "10 mg",
                "route": None,
                "frequency": "kuniga 1 marta",
                "duration": None,
                "instructions": None,
                "evidence": [2, 99],
            }
        ],
        "not_mentioned": ["history_life"],
    },
    ensure_ascii=False,
)
