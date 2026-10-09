from scribe.providers import ProviderError, STTSpec
from scribe.stt.base import STTClient, STTResult


def make_stt(spec: STTSpec) -> STTClient:
    if spec.provider == "elevenlabs":
        from scribe.stt.elevenlabs import ElevenLabsSTT

        return ElevenLabsSTT(spec)
    if spec.provider == "openai":
        from scribe.stt.openai_stt import OpenAICompatibleSTT

        return OpenAICompatibleSTT(spec)
    if spec.provider == "fake":
        from scribe.stt.fake import FakeSTT

        return FakeSTT(spec)
    raise ProviderError(f"Unsupported STT provider type '{spec.provider}' for '{spec.id}'")


__all__ = ["make_stt", "STTClient", "STTResult"]
