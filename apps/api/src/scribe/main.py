import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scribe.config import Settings, get_settings
from scribe.db import Encounter, make_session_factory
from scribe.notes.prompt import SPECIALTIES
from scribe.notes.schema import OUTPUT_LANGUAGES
from scribe.pipeline import generate_note_run, process_encounter
from scribe.providers import ProviderError, Registry, load_registry
from scribe.storage import audio_store_from

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ALLOWED_MIME_PREFIXES = ("audio/", "video/webm", "video/mp4", "video/ogg", "application/octet-stream")


class RegenerateRequest(BaseModel):
    llm_model: str
    output_language: str | None = None


def create_app(settings: Settings | None = None, registry: Registry | None = None) -> FastAPI:
    settings = settings or get_settings()
    registry = registry or load_registry(settings.providers_file)
    sessions = make_session_factory(settings.database_url)
    store = audio_store_from(settings)
    registry.get_stt(settings.stt_provider)  # fail fast on a misconfigured default
    registry.get_llm(settings.llm_model)

    app = FastAPI(title="azuziz scribe API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings, app.state.registry, app.state.sessions, app.state.store = settings, registry, sessions, store

    def get_db(request: Request):
        with request.app.state.sessions() as db:
            yield db

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/config")
    def config() -> dict:
        llms = [{"id": s.id, "label": s.label, "available": s.has_key()} for s in registry.llm.values() if s.drafting]
        stt = registry.get_stt(settings.stt_provider)
        return {
            "default_llm": settings.llm_model,
            "llms": llms,
            "stt_provider": {"id": stt.id, "label": stt.label},
            "output_languages": list(OUTPUT_LANGUAGES),
            "specialties": list(SPECIALTIES),
            "demo_mode": stt.provider == "fake" or registry.get_llm(settings.llm_model).provider == "fake",
            "max_upload_mb": settings.max_upload_mb,
        }

    @app.post("/api/encounters", status_code=202)
    async def create_encounter(
        background: BackgroundTasks,
        audio: Annotated[UploadFile, File()],
        consent: Annotated[bool, Form()] = False,
        output_language: Annotated[str, Form()] = "uz-Latn",
        specialty: Annotated[str, Form()] = "therapist",
        llm_model: Annotated[str | None, Form()] = None,
        db=Depends(get_db),
    ) -> dict:
        if not consent:
            raise HTTPException(400, "The patient's consent to recording is required")
        if output_language not in OUTPUT_LANGUAGES:
            raise HTTPException(400, f"output_language must be one of {OUTPUT_LANGUAGES}")
        if specialty not in SPECIALTIES:
            raise HTTPException(400, f"specialty must be one of {list(SPECIALTIES)}")
        model_id = llm_model or settings.llm_model
        _check_llm(registry, model_id)
        mime = (audio.content_type or "application/octet-stream").split(";")[0].strip()
        if not mime.startswith(ALLOWED_MIME_PREFIXES):
            raise HTTPException(415, f"Unsupported file type {mime}")
        limit = settings.max_upload_mb * 1024 * 1024
        buf = bytearray()
        while chunk := await audio.read(1024 * 1024):
            buf += chunk
            if len(buf) > limit:
                raise HTTPException(413, f"Audio is larger than {settings.max_upload_mb} MB")
        data = bytes(buf)
        if not data:
            raise HTTPException(400, "Empty audio file")

        enc = Encounter(
            consent_given=True,
            consent_at=datetime.now(UTC),
            output_language=output_language,
            specialty=specialty,
            stt_provider=settings.stt_provider,
            audio_ref=store.save(data),
            audio_filename=(audio.filename or "audio")[:128],
            audio_mime=mime,
            audio_bytes=len(data),
            note_runs=[],
        )
        db.add(enc)
        db.commit()
        background.add_task(process_encounter, enc.id, model_id, sessions, store, registry, settings.llm_max_retries)
        return {"id": enc.id, "status": enc.status}

    @app.get("/api/encounters")
    def list_encounters(db=Depends(get_db)) -> list[dict]:
        rows = db.query(Encounter).order_by(Encounter.created_at.desc()).limit(50).all()
        return [_summary(e) for e in rows]

    @app.get("/api/encounters/{encounter_id}")
    def get_encounter(encounter_id: str, db=Depends(get_db)) -> dict:
        enc = db.get(Encounter, encounter_id)
        if enc is None:
            raise HTTPException(404, "Encounter not found")
        return {
            **_summary(enc),
            "error": enc.error,
            "transcript": enc.transcript,
            "stt_metrics": enc.stt_metrics,
            "note_runs": enc.note_runs,
        }

    @app.post("/api/encounters/{encounter_id}/notes", status_code=202)
    def regenerate(encounter_id: str, body: RegenerateRequest, background: BackgroundTasks, db=Depends(get_db)):
        enc = db.get(Encounter, encounter_id)
        if enc is None:
            raise HTTPException(404, "Encounter not found")
        if enc.transcript is None:
            raise HTTPException(409, "The transcript isn't ready yet")
        if body.output_language and body.output_language not in OUTPUT_LANGUAGES:
            raise HTTPException(400, f"output_language must be one of {OUTPUT_LANGUAGES}")
        _check_llm(registry, body.llm_model)
        enc.status = "generating"
        db.commit()
        background.add_task(
            generate_note_run,
            enc.id,
            body.llm_model,
            body.output_language,
            sessions,
            registry,
            settings.llm_max_retries,
        )
        return {"id": enc.id, "status": "generating"}

    return app


def _check_llm(registry: Registry, model_id: str) -> None:
    try:
        spec = registry.get_llm(model_id)
    except ProviderError as e:
        raise HTTPException(400, str(e)) from None
    if not spec.has_key():
        raise HTTPException(400, f"Model '{model_id}' has no API key configured ({spec.api_key_env})")


def _summary(enc: Encounter) -> dict:
    return {
        "id": enc.id,
        "created_at": enc.created_at.isoformat() if enc.created_at else None,
        "status": enc.status,
        "output_language": enc.output_language,
        "specialty": enc.specialty,
        "stt_provider": enc.stt_provider,
        "audio_bytes": enc.audio_bytes,
        "note_count": len(enc.note_runs or []),
    }


def app_factory() -> FastAPI:
    """Entry point for `uvicorn --factory scribe.main:app_factory`."""
    return create_app()
