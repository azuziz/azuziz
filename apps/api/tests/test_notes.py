import json

import pytest

from scribe.llm.client import parse_json
from scribe.notes.generator import NoteGenerationError, generate_note
from scribe.notes.prompt import build_messages
from scribe.notes.schema import Note, render_text, strict_json_schema
from tests.conftest import VALID_NOTE, ScriptedClient


def _objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            yield node
        for v in node.values():
            yield from _objects(v)
    elif isinstance(node, list):
        for v in node:
            yield from _objects(v)


def test_strict_schema_requires_every_property_and_forbids_extras():
    schema = strict_json_schema(Note)
    objects = list(_objects(schema))
    assert len(objects) >= 8
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])
    assert "default" not in json.dumps(schema)


def test_generate_note_retries_with_the_validation_error(transcript):
    client = ScriptedClient(replies=['{"complaints": "not an object"}', VALID_NOTE])
    result = generate_note(client, transcript, "uz-Latn", "therapist", max_retries=1)

    assert result.attempts == 2
    assert "not valid JSON for the schema" in client.calls[1][-1]["content"]
    assert result.note.medications[0].dose == "10 mg"
    # evidence id 99 doesn't exist in the transcript and is dropped
    assert result.note.medications[0].evidence == [2]
    assert result.dropped_evidence == 1
    # two calls: 2000 input (400 cached), 1000 output at $1 / $0.1 / $2 per MTok
    assert result.usage.input_tokens == 2000
    assert result.cost_usd == pytest.approx((1600 * 1.0 + 400 * 0.1 + 1000 * 2.0) / 1e6)


def test_generate_note_gives_up_after_max_retries(transcript):
    client = ScriptedClient(replies=["nonsense", "still nonsense"])
    with pytest.raises(NoteGenerationError) as e:
        generate_note(client, transcript, "ru", "therapist", max_retries=1)
    assert e.value.attempts == 2
    assert e.value.usage.calls == 2


def test_parse_json_accepts_a_fenced_reply():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('{"a": 1}') == {"a": 1}


def test_prompt_puts_stable_text_first_and_numbers_segments(transcript):
    system, user = build_messages(transcript, "uz-Latn", "therapist")
    assert system["role"] == "system" and "Uzbek in the official Latin alphabet" in system["content"]
    assert "not_mentioned" in system["content"]
    assert "[2] doctor: Amlodipin 10 milligramm" in user["content"]


def test_render_text_uses_headings_of_the_note_language():
    note = Note.model_validate_json(VALID_NOTE)
    note.allergies_denied = True
    uz = render_text(note, "uz-Latn")
    ru = render_text(note, "ru")
    assert uz.startswith("Shikoyatlar:\nBosh ogʻrigʻi")
    assert "Allergiya inkor etiladi" in uz
    assert "Davolash:\n- amlodipin — 10 mg, kuniga 1 marta" in uz
    assert ru.startswith("Жалобы:")
    assert "Аллергию отрицает" in ru
    # sections that weren't discussed are omitted rather than printed empty
    assert "Hayot anamnezi" not in uz
