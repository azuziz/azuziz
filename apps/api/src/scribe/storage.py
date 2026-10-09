"""Audio storage, encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256)."""

import logging
import uuid
from pathlib import Path

from cryptography.fernet import Fernet

from scribe.config import Settings

log = logging.getLogger(__name__)


class AudioStore:
    def __init__(self, root: Path, key: bytes):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(key)

    def save(self, data: bytes) -> str:
        name = f"{uuid.uuid4().hex}.bin"
        (self.root / name).write_bytes(self._fernet.encrypt(data))
        return name

    def load(self, name: str) -> bytes:
        return self._fernet.decrypt(self._path(name).read_bytes())

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def _path(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if path.parent != self.root.resolve():
            raise ValueError("invalid audio reference")
        return path


def audio_store_from(settings: Settings) -> AudioStore:
    key = settings.audio_encryption_key
    if not key:
        if settings.is_production:
            raise RuntimeError("AUDIO_ENCRYPTION_KEY must be set in production")
        # Development only: keep a local key next to the data so restarts can still read old audio.
        key_file = settings.storage_dir / ".dev-key"
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        if not key_file.exists():
            key_file.write_bytes(Fernet.generate_key())
            log.warning("No AUDIO_ENCRYPTION_KEY set; generated a development key at %s", key_file)
        key = key_file.read_bytes().decode()
    return AudioStore(settings.storage_dir, key.encode())
