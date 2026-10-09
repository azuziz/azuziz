"""One client for every OpenAI-compatible chat API (OpenAI, Xiaomi MiMo, Moonshot Kimi, OpenRouter)."""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from scribe.providers import LLMSpec, ProviderError

log = logging.getLogger(__name__)


@dataclass
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    calls: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += other.input_tokens
        self.cached_input_tokens += other.cached_input_tokens
        self.output_tokens += other.output_tokens
        self.latency_s += other.latency_s
        self.calls += other.calls

    def cost_usd(self, spec: LLMSpec) -> float:
        uncached = max(self.input_tokens - self.cached_input_tokens, 0)
        return (
            uncached * spec.price_input
            + self.cached_input_tokens * spec.price_cached_input
            + self.output_tokens * spec.price_output
        ) / 1_000_000


@dataclass
class ChatResult:
    content: str
    usage: Usage
    structured_output_used: str


@dataclass
class JsonSchemaFormat:
    name: str
    schema: dict[str, Any]


class ChatClient(Protocol):
    spec: LLMSpec

    def chat(self, messages: list[dict[str, str]], fmt: JsonSchemaFormat) -> ChatResult: ...


@dataclass
class OpenAICompatibleClient:
    spec: LLMSpec
    timeout_s: float = 180.0
    _client: Any = field(default=None, init=False, repr=False)
    _schema_rejected: bool = field(default=False, init=False)

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.spec.api_key(), base_url=self.spec.base_url, timeout=self.timeout_s, max_retries=2
            )
        return self._client

    def chat(self, messages: list[dict[str, str]], fmt: JsonSchemaFormat) -> ChatResult:
        from openai import BadRequestError

        mode = self.spec.structured_output
        if mode == "json_schema" and self._schema_rejected:
            mode = "json_object"
        try:
            return self._call(messages, fmt, mode)
        except BadRequestError as e:
            # Some OpenAI-compatible APIs reject json_schema; JSON mode plus our own validation still works.
            if mode != "json_schema":
                raise
            log.warning("%s rejected json_schema (%s); falling back to json_object", self.spec.id, e)
            self._schema_rejected = True
            return self._call(messages, fmt, "json_object")

    def _call(self, messages: list[dict[str, str]], fmt: JsonSchemaFormat, mode: str) -> ChatResult:
        if mode == "json_schema":
            response_format: dict[str, Any] = {
                "type": "json_schema",
                "json_schema": {"name": fmt.name, "schema": fmt.schema, "strict": True},
            }
        else:
            response_format = {"type": "json_object"}
        started = time.perf_counter()
        resp = self._get_client().chat.completions.create(
            model=self.spec.model,
            messages=messages,
            response_format=response_format,
            **self.spec.params,
        )
        latency = time.perf_counter() - started
        content = resp.choices[0].message.content or ""
        return ChatResult(content=content, usage=_usage_from(resp, latency), structured_output_used=mode)


def _usage_from(resp: Any, latency: float) -> Usage:
    u = getattr(resp, "usage", None)
    if u is None:
        return Usage(latency_s=latency, calls=1)
    cached = 0
    details = getattr(u, "prompt_tokens_details", None)
    if details is not None and getattr(details, "cached_tokens", None):
        cached = details.cached_tokens
    elif getattr(u, "cached_tokens", None):  # Moonshot reports it at the top level
        cached = u.cached_tokens
    return Usage(
        input_tokens=u.prompt_tokens or 0,
        cached_input_tokens=cached or 0,
        output_tokens=u.completion_tokens or 0,
        latency_s=latency,
        calls=1,
    )


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_json(content: str) -> Any:
    """Parses a JSON reply, tolerating a ```json fence around it."""
    m = _FENCE.match(content)
    return json.loads(m.group(1) if m else content)


def make_client(spec: LLMSpec) -> ChatClient:
    if spec.provider == "fake":
        from scribe.llm.fake import FakeChatClient

        return FakeChatClient(spec)
    if spec.provider != "openai_compatible":
        raise ProviderError(f"Unsupported LLM provider type '{spec.provider}' for '{spec.id}'")
    return OpenAICompatibleClient(spec)
