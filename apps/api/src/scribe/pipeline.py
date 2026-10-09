"""Audio -> transcript -> note. Runs in the background after an upload."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from scribe.db import Encounter
from scribe.llm.client import make_client
from scribe.notes.generator import NoteGenerationError, generate_note
from scribe.notes.schema import render_sections, render_text
from scribe.providers import Registry
from scribe.storage import AudioStore
from scribe.stt import make_stt
from scribe.transcript import Transcript

log = logging.getLogger(__name__)


def process_encounter(
    encounter_id: str,
    llm_model: str,
    sessions: sessionmaker,
    store: AudioStore,
    registry: Registry,
    max_retries: int = 1,
) -> None:
    with sessions() as db:
        enc = db.get(Encounter, encounter_id)
        if enc is None:
            return
        try:
            enc.status = "transcribing"
            db.commit()
            stt = make_stt(registry.get_stt(enc.stt_provider))
            result = stt.transcribe(store.load(enc.audio_ref), enc.audio_filename, enc.audio_mime)
            enc.transcript = result.transcript.model_dump()
            enc.stt_metrics = {
                "provider": enc.stt_provider,
                "stt_latency_s": round(result.latency_s, 2),
                "stt_cost_usd": result.cost_usd,
                "duration_s": result.transcript.duration_s,
                "language": result.transcript.language,
            }
            enc.status = "generating"
            db.commit()
        except Exception as e:  # noqa: BLE001 - any provider failure is shown to the user
            log.exception("transcription failed for %s", encounter_id)
            enc.status, enc.error = "failed", f"Transcription failed: {e}"
            db.commit()
            return
    generate_note_run(encounter_id, llm_model, None, sessions, registry, max_retries)


def generate_note_run(
    encounter_id: str,
    llm_model: str,
    output_language: str | None,
    sessions: sessionmaker,
    registry: Registry,
    max_retries: int = 1,
) -> None:
    """Drafts a note from the stored transcript and appends it to the encounter's note runs."""
    with sessions() as db:
        enc = db.get(Encounter, encounter_id)
        if enc is None or enc.transcript is None:
            return
        language = output_language or enc.output_language
        enc.status, enc.error = "generating", None
        db.commit()
        try:
            client = make_client(registry.get_llm(llm_model))
            result = generate_note(
                client, Transcript.model_validate(enc.transcript), language, enc.specialty, max_retries
            )
            run = {
                "model": llm_model,
                "output_language": language,
                "note": result.note.model_dump(),
                "sections": render_sections(result.note, language),
                "text": render_text(result.note, language),
                "metrics": result.metrics(),
                "warnings": result.warnings,
                "created_at": datetime.now(UTC).isoformat(),
            }
        except NoteGenerationError as e:
            run = _failed_run(llm_model, language, str(e))
        except Exception as e:  # noqa: BLE001
            log.exception("note generation failed for %s", encounter_id)
            run = _failed_run(llm_model, language, f"Note generation failed: {e}")
        enc.note_runs = [*enc.note_runs, run]
        flag_modified(enc, "note_runs")
        failed = "error" in run
        enc.status = "failed" if failed and not any("error" not in r for r in enc.note_runs) else "done"
        enc.error = run.get("error") if failed else None
        db.commit()


def _failed_run(model: str, language: str, error: str) -> dict:
    return {
        "model": model,
        "output_language": language,
        "error": error,
        "created_at": datetime.now(UTC).isoformat(),
    }
