import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # uploaded -> transcribing -> generating -> done | failed
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    output_language: Mapped[str] = mapped_column(String(8))
    specialty: Mapped[str] = mapped_column(String(32))
    stt_provider: Mapped[str] = mapped_column(String(64))

    audio_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_filename: Mapped[str] = mapped_column(String(128), default="audio")
    audio_mime: Mapped[str] = mapped_column(String(64), default="application/octet-stream")
    audio_bytes: Mapped[int] = mapped_column(Integer, default=0)

    transcript: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stt_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # One entry per note generation: {"model", "output_language", "note", "metrics", "warnings", "created_at"}.
    # Regenerating with another model appends, so models can be compared on the same transcript.
    note_runs: Mapped[list] = mapped_column(JSON, default=list)


def make_session_factory(database_url: str) -> sessionmaker:
    if database_url.startswith("sqlite:///"):
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)  # Alembic migrations arrive with Postgres in Sprint 2
    return sessionmaker(engine, expire_on_commit=False)
