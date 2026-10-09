"""Loads the STT and LLM provider registry from providers.toml."""

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from scribe.config import get_settings


class ProviderError(RuntimeError):
    """A provider is unknown, misconfigured, or failed."""


@dataclass(frozen=True)
class LLMSpec:
    id: str
    label: str
    model: str
    provider: str = "openai_compatible"
    base_url: str | None = None
    api_key_env: str | None = None
    structured_output: str = "json_schema"
    price_input: float = 0.0
    price_cached_input: float = 0.0
    price_output: float = 0.0
    drafting: bool = True  # false for models used only as the eval judge
    params: dict[str, Any] = field(default_factory=dict)

    def api_key(self) -> str:
        return _require_key(self.api_key_env, self.id)

    def has_key(self) -> bool:
        return self.provider == "fake" or bool(self.api_key_env and os.environ.get(self.api_key_env))


@dataclass(frozen=True)
class STTSpec:
    id: str
    label: str
    provider: str
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    price_per_minute: float | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def api_key(self) -> str:
        return _require_key(self.api_key_env, self.id)

    def has_key(self) -> bool:
        return self.provider == "fake" or bool(self.api_key_env and os.environ.get(self.api_key_env))


@dataclass(frozen=True)
class Registry:
    llm: dict[str, LLMSpec]
    stt: dict[str, STTSpec]

    def get_llm(self, model_id: str) -> LLMSpec:
        try:
            return self.llm[model_id]
        except KeyError:
            raise ProviderError(f"Unknown LLM '{model_id}'. Known: {', '.join(self.llm)}") from None

    def get_stt(self, stt_id: str) -> STTSpec:
        try:
            return self.stt[stt_id]
        except KeyError:
            raise ProviderError(f"Unknown STT provider '{stt_id}'. Known: {', '.join(self.stt)}") from None


def _require_key(env_name: str | None, provider_id: str) -> str:
    key = os.environ.get(env_name) if env_name else None
    if not key:
        raise ProviderError(f"Provider '{provider_id}' needs the environment variable {env_name}")
    return key


def load_registry(path: Path) -> Registry:
    with path.open("rb") as f:
        data = tomllib.load(f)
    llm = {mid: LLMSpec(id=mid, **cfg) for mid, cfg in data.get("llm", {}).items()}
    stt = {sid: STTSpec(id=sid, **cfg) for sid, cfg in data.get("stt", {}).items()}
    return Registry(llm=llm, stt=stt)


@lru_cache
def get_registry() -> Registry:
    return load_registry(get_settings().providers_file)
