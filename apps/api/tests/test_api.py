from cryptography.fernet import Fernet

from scribe.storage import AudioStore

AUDIO = ("visit.webm", b"\x1a\x45\xdf\xa3 fake webm bytes", "audio/webm")


def _upload(client, **form):
    data = {"consent": "true", "output_language": "uz-Latn", "specialty": "therapist", **form}
    return client.post("/api/encounters", data=data, files={"audio": AUDIO})


def test_config_reports_demo_mode_and_models(client):
    cfg = client.get("/api/config").json()
    assert cfg["demo_mode"] is True
    ids = {m["id"] for m in cfg["llms"]}
    assert {"gpt-6-luna", "mimo-v2.6-pro", "kimi-k2.6", "kimi-k3", "fake"} <= ids
    assert "gpt-6-sol" not in ids  # judge only
    assert cfg["output_languages"] == ["uz-Latn", "uz-Cyrl", "ru"]


def test_recording_requires_consent(client):
    resp = _upload(client, consent="false")
    assert resp.status_code == 400
    assert "consent" in resp.json()["detail"]


def test_upload_transcribes_and_drafts_a_note(client, settings):
    resp = _upload(client)
    assert resp.status_code == 202
    enc_id = resp.json()["id"]

    enc = client.get(f"/api/encounters/{enc_id}").json()  # background task has run by now
    assert enc["status"] == "done", enc["error"]
    assert len(enc["transcript"]["segments"]) > 3
    run = enc["note_runs"][0]
    assert run["model"] == "fake"
    assert run["text"].startswith("Shikoyatlar:")
    assert run["sections"][0]["key"] == "complaints"
    assert run["sections"][0]["heading"] == "Shikoyatlar"
    assert run["sections"][0]["evidence"] == [1]  # the first patient turn of the demo transcript
    assert run["metrics"]["attempts"] == 1

    # audio is encrypted at rest
    stored = list(settings.storage_dir.glob("*.bin"))
    assert len(stored) == 1
    assert AUDIO[1] not in stored[0].read_bytes()


def test_regenerate_appends_a_run_for_comparison(client):
    enc_id = _upload(client).json()["id"]
    resp = client.post(f"/api/encounters/{enc_id}/notes", json={"llm_model": "fake", "output_language": "ru"})
    assert resp.status_code == 202
    runs = client.get(f"/api/encounters/{enc_id}").json()["note_runs"]
    assert [r["output_language"] for r in runs] == ["uz-Latn", "ru"]
    assert runs[1]["text"].startswith("Жалобы:")


def test_models_without_a_key_are_rejected_up_front(client, monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    resp = _upload(client, llm_model="kimi-k3")
    assert resp.status_code == 400
    assert "MOONSHOT_API_KEY" in resp.json()["detail"]
    assert _upload(client, llm_model="no-such-model").status_code == 400


def test_rejects_non_audio_and_empty_uploads(client):
    data = {"consent": "true"}
    assert (
        client.post("/api/encounters", data=data, files={"audio": ("x.pdf", b"%PDF", "application/pdf")}).status_code
        == 415
    )
    assert client.post("/api/encounters", data=data, files={"audio": ("x.webm", b"", "audio/webm")}).status_code == 400


def test_audio_store_round_trip_and_path_safety(tmp_path):
    store = AudioStore(tmp_path, Fernet.generate_key())
    ref = store.save(b"hello")
    assert store.load(ref) == b"hello"
    try:
        store.load("../escape.bin")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal was not rejected")
