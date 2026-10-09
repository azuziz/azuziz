from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError

from scribe.llm.client import JsonSchemaFormat, OpenAICompatibleClient
from scribe.providers import LLMSpec

SPEC = LLMSpec(id="kimi", label="Kimi", model="kimi-k2.6", base_url="http://x/v1", structured_output="json_schema")
FMT = JsonSchemaFormat(name="clinical_note", schema={"type": "object"})


def _response(content: str, usage: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=usage)


class FakeCompletions:
    def __init__(self, reject_schema: bool, usage: SimpleNamespace):
        self.reject_schema, self.usage, self.formats = reject_schema, usage, []

    def create(self, **kwargs):
        self.formats.append(kwargs["response_format"]["type"])
        if self.reject_schema and kwargs["response_format"]["type"] == "json_schema":
            response = httpx.Response(400, request=httpx.Request("POST", "http://x/v1/chat/completions"))
            raise BadRequestError("json_schema not supported", response=response, body=None)
        return _response("{}", self.usage)


def _client(reject_schema: bool, usage: SimpleNamespace) -> tuple[OpenAICompatibleClient, FakeCompletions]:
    completions = FakeCompletions(reject_schema, usage)
    c = OpenAICompatibleClient(SPEC)
    c._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return c, completions


def test_falls_back_to_json_mode_once_and_remembers():
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_tokens_details=None, cached_tokens=None)
    c, completions = _client(reject_schema=True, usage=usage)

    first = c.chat([{"role": "user", "content": "hi"}], FMT)
    second = c.chat([{"role": "user", "content": "hi"}], FMT)

    assert first.structured_output_used == "json_object"
    assert second.structured_output_used == "json_object"
    assert completions.formats == ["json_schema", "json_object", "json_object"]


def test_reads_cached_tokens_from_openai_and_moonshot_usage_shapes():
    openai_usage = SimpleNamespace(
        prompt_tokens=1000, completion_tokens=10, prompt_tokens_details=SimpleNamespace(cached_tokens=800)
    )
    moonshot_usage = SimpleNamespace(
        prompt_tokens=1000, completion_tokens=10, prompt_tokens_details=None, cached_tokens=600
    )
    assert _client(False, openai_usage)[0].chat([], FMT).usage.cached_input_tokens == 800
    assert _client(False, moonshot_usage)[0].chat([], FMT).usage.cached_input_tokens == 600


def test_real_sdk_round_trip_over_http(transcript):
    """Drives the actual openai SDK against a mock OpenAI-compatible server: checks what we send and parse."""
    import json

    from openai import OpenAI

    from scribe.notes.generator import generate_note
    from tests.conftest import VALID_NOTE

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.update(path=request.url.path, auth=request.headers["authorization"], body=body)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": VALID_NOTE}}
                ],
                "usage": {
                    "prompt_tokens": 3000,
                    "completion_tokens": 900,
                    "total_tokens": 3900,
                    "prompt_tokens_details": {"cached_tokens": 1000},
                },
            },
        )

    spec = LLMSpec(
        id="gpt-6-luna",
        label="Luna",
        model="gpt-6-luna",
        base_url="https://api.example.test/v1",
        price_input=0.10,
        price_cached_input=0.01,
        price_output=0.50,
    )
    client = OpenAICompatibleClient(spec)
    client._client = OpenAI(
        api_key="sk-test", base_url=spec.base_url, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = generate_note(client, transcript, "uz-Latn", "therapist")

    assert seen["path"] == "/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "gpt-6-luna"
    fmt = seen["body"]["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]
    assert result.note.medications[0].drug == "amlodipin"
    assert result.usage.cached_input_tokens == 1000
    assert result.cost_usd == pytest.approx((2000 * 0.10 + 1000 * 0.01 + 900 * 0.50) / 1e6)
