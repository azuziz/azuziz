import json
import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from scribe.llm.client import ChatClient, JsonSchemaFormat, Usage, parse_json
from scribe.notes.prompt import build_messages
from scribe.notes.schema import Note, strict_json_schema
from scribe.transcript import Transcript

log = logging.getLogger(__name__)

NOTE_FORMAT = JsonSchemaFormat(name="clinical_note", schema=strict_json_schema(Note))


class NoteGenerationError(RuntimeError):
    def __init__(self, message: str, usage: Usage, attempts: int):
        super().__init__(message)
        self.usage = usage
        self.attempts = attempts


@dataclass
class NoteResult:
    note: Note
    model_id: str
    usage: Usage
    cost_usd: float
    attempts: int  # 1 = valid on the first try
    dropped_evidence: int  # evidence ids that pointed at non-existent segments
    structured_output: str
    warnings: list[str] = field(default_factory=list)

    def metrics(self) -> dict:
        return {
            "model": self.model_id,
            "input_tokens": self.usage.input_tokens,
            "cached_input_tokens": self.usage.cached_input_tokens,
            "output_tokens": self.usage.output_tokens,
            "llm_latency_s": round(self.usage.latency_s, 2),
            "llm_cost_usd": round(self.cost_usd, 6),
            "attempts": self.attempts,
            "dropped_evidence": self.dropped_evidence,
            "structured_output": self.structured_output,
        }


def generate_note(
    client: ChatClient,
    transcript: Transcript,
    output_language: str,
    specialty: str,
    max_retries: int = 1,
) -> NoteResult:
    """Drafts a note; if the reply isn't valid against the schema, shows the model the error and retries."""
    messages = build_messages(transcript, output_language, specialty)
    usage = Usage()
    last_error = ""
    for attempt in range(1, max_retries + 2):
        result = client.chat(messages, NOTE_FORMAT)
        usage.add(result.usage)
        try:
            note = Note.model_validate(parse_json(result.content))
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = str(e)[:2000]
            log.warning("%s attempt %d returned an invalid note: %s", client.spec.id, attempt, last_error[:300])
            messages = messages + [
                {"role": "assistant", "content": result.content},
                {
                    "role": "user",
                    "content": "Your reply was not valid JSON for the schema. Error:\n"
                    f"{last_error}\nReturn the corrected JSON object only.",
                },
            ]
            continue
        dropped = note.drop_unknown_evidence(transcript.segment_ids)
        warnings = [f"{dropped} evidence reference(s) pointed at non-existent segments"] if dropped else []
        return NoteResult(
            note=note,
            model_id=client.spec.id,
            usage=usage,
            cost_usd=usage.cost_usd(client.spec),
            attempts=attempt,
            dropped_evidence=dropped,
            structured_output=result.structured_output_used,
            warnings=warnings,
        )
    raise NoteGenerationError(
        f"{client.spec.id} did not return a valid note after {max_retries + 1} attempts: {last_error[:500]}",
        usage=usage,
        attempts=max_retries + 1,
    )
