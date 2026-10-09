import httpx
import pytest

from scribe.providers import STTSpec
from scribe.stt import base, elevenlabs, openai_stt
from scribe.stt.base import words_to_segments


def _w(text, start, end, speaker="speaker_0", kind="word"):
    return {"text": text, "start": start, "end": end, "speaker_id": speaker, "type": kind}


ELEVENLABS_BODY = {
    "language_code": "uzb",
    "text": "Nima bezovta? Boshim og'riyapti.",
    "words": [
        _w("Nima", 0.0, 0.3),
        _w(" ", 0.3, 0.35, kind="spacing"),
        _w("bezovta?", 0.35, 0.9),
        _w(" ", 0.9, 1.0, kind="spacing"),
        _w("Boshim", 1.0, 1.4, speaker="speaker_1"),
        _w(" ", 1.4, 1.45, speaker="speaker_1", kind="spacing"),
        _w("og'riyapti.", 1.45, 2.1, speaker="speaker_1"),
        _w("(yo'tal)", 2.1, 2.3, speaker="speaker_1", kind="audio_event"),
    ],
}


def test_elevenlabs_words_are_grouped_into_speaker_segments():
    t = elevenlabs.parse_response(ELEVENLABS_BODY)
    assert [(s.speaker, s.text) for s in t.segments] == [
        ("speaker_0", "Nima bezovta?"),
        ("speaker_1", "Boshim og'riyapti."),
    ]
    assert t.segments[1].start == 1.0 and t.segments[1].end == 2.1
    assert t.language == "uzb"
    assert t.duration_s == 2.1


def test_long_pause_starts_a_new_segment_for_the_same_speaker():
    words = [
        {"text": "Bir", "start": 0.0, "end": 0.5, "speaker": "a"},
        {"text": " ikki", "start": 5.0, "end": 5.5, "speaker": "a"},
    ]
    assert [s.text for s in words_to_segments(words)] == ["Bir", "ikki"]


def test_elevenlabs_request_and_cost(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    captured = {}

    def fake_post(url, headers, data, files, timeout):
        captured.update(url=url, headers=headers, data=data, files=files)
        return httpx.Response(200, json=ELEVENLABS_BODY)

    monkeypatch.setattr(base.httpx, "post", fake_post)
    spec = STTSpec(
        id="elevenlabs",
        label="EL",
        provider="elevenlabs",
        model="scribe_v2",
        base_url="https://api.elevenlabs.io/v1",
        api_key_env="ELEVENLABS_API_KEY",
        price_per_minute=0.6,
    )
    result = elevenlabs.ElevenLabsSTT(spec).transcribe(b"audio", "a.webm", "audio/webm")

    assert captured["url"] == "https://api.elevenlabs.io/v1/speech-to-text"
    assert captured["headers"] == {"xi-api-key": "k"}
    assert captured["data"]["model_id"] == "scribe_v2" and captured["data"]["diarize"] == "true"
    assert "language_code" not in captured["data"]  # mixed UZ/RU: let the model detect
    assert result.cost_usd == pytest.approx(0.6 * 2.1 / 60, abs=1e-6)
    assert result.transcript.provider == "elevenlabs"


def test_openai_transcription_with_and_without_segments():
    with_segments = openai_stt.parse_response(
        {"text": "a b", "language": "uzbek", "duration": 3.0, "segments": [{"start": 0, "end": 1, "text": " a "}]}
    )
    assert [s.text for s in with_segments.segments] == ["a"]
    assert with_segments.duration_s == 3.0
    plain = openai_stt.parse_response({"text": "Salom doktor"})
    assert [s.text for s in plain.segments] == ["Salom doktor"]


def test_stt_post_retries_transient_failures(monkeypatch):
    calls = []
    replies = [httpx.ConnectError("reset"), httpx.Response(503), httpx.Response(200, json={"ok": True})]

    def flaky_post(url, **kwargs):
        calls.append(url)
        reply = replies[len(calls) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(base.httpx, "post", flaky_post)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    assert base.post_with_retry("https://stt.example/x", attempts=3).status_code == 200
    assert len(calls) == 3

    # client errors are not retried
    calls.clear()
    replies[:] = [httpx.Response(401)]
    assert base.post_with_retry("https://stt.example/x", attempts=3).status_code == 401
    assert len(calls) == 1
