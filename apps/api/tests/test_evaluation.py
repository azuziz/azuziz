import json
import shutil

import pytest

from scribe.config import API_ROOT
from scribe.evaluation.cases import load_case, load_cases
from scribe.evaluation.judge import keyword_grade, llm_grade
from scribe.evaluation.llm_compare import run_comparison
from scribe.evaluation.stt_bakeoff import run_bakeoff
from scribe.evaluation.text import cer, keywords_found, normalize, term_recall, wer, wrong_script_ratio
from scribe.notes.schema import Note
from scribe.providers import load_registry
from tests.conftest import ScriptedClient

CASES_DIR = API_ROOT.parents[1] / "eval" / "cases"


def test_normalize_unifies_uzbek_apostrophes_and_keeps_decimals():
    assert normalize("Oʻzbekiston, Gʻulom!") == normalize("O'zbekiston gʼulom") == "o'zbekiston g'ulom"
    assert normalize("Qand 9,8 mmol.") == "qand 9,8 mmol"
    assert normalize("Ёлка") == "елка"


def test_wer_and_cer():
    assert wer("boshim og'riyapti", "boshim ogʻriyapti") == 0.0
    assert wer("bir ikki uch", "bir uch") == pytest.approx(1 / 3)
    assert cer("abc", "abd") == pytest.approx(1 / 3)


def test_keyword_groups_and_term_recall():
    assert keywords_found(["amlodipin", "10|o'n"], "Amlodipin 10 mg")
    assert not keywords_found(["amlodipin", "10"], "Amlodipin 5 mg")
    assert term_recall(["kreatinin", "EKG"], "kreatinin va ekg") == 1.0
    assert term_recall([], "x") is None


def test_wrong_script_ratio():
    assert wrong_script_ratio("Bosh ogʻrigʻi", "uz-Latn") == 0.0
    assert wrong_script_ratio("Bosh огриги", "uz-Latn") > 0.5
    assert wrong_script_ratio("Жалобы на боль", "ru") == 0.0


def test_all_eval_cases_load_and_reference_valid_facts():
    cases = load_cases(CASES_DIR)
    assert len(cases) >= 4
    for c in cases:
        assert c.output_language in ("uz-Latn", "uz-Cyrl", "ru")
        assert len(c.transcript().segments) == len(c.segments)
        assert len({f.id for f in c.facts}) == len(c.facts)
        assert any(f.critical for f in c.facts)


def test_llm_judge_counts_wrong_critical_facts_as_critical_errors():
    case = load_case(CASES_DIR / "02-pediatric-arvi-ru")
    verdict = {
        "facts": [{"id": f.id, "status": "captured", "comment": ""} for f in case.facts if f.id != "f10"]
        + [{"id": "f10", "status": "wrong", "comment": "kept the pre-correction 5 ml dose"}],
        "unsupported": [{"statement": "амоксициллин", "severity": "critical", "reason": "never prescribed"}],
    }
    judge = ScriptedClient(replies=[json.dumps(verdict)])
    grade = llm_grade(judge, case, "Жалобы: ...")
    assert grade.critical_errors(case) == 2  # one wrong critical fact + one critical hallucination
    assert grade.recall() == pytest.approx((len(case.facts) - 1) / len(case.facts))
    assert "Ключевые" not in judge.calls[0][1]["content"]  # prompt is in English
    assert "f10 (critical)" in judge.calls[0][1]["content"]


def test_keyword_grade_on_a_good_note():
    case = load_case(CASES_DIR / "04-tonsillitis-mixed-allergy")
    note = Note.model_validate(
        {
            "medications": [
                {"drug": "Азитромицин", "dose": "500 мг", "frequency": "1 раз в день", "duration": "3 дня"}
            ],
            "allergies": [{"substance": "амоксициллин", "reaction": "сыпь"}],
        }
    )
    facts = keyword_grade(case, note).facts
    assert facts["f8"] == "captured"
    assert facts["f4"] == "captured"
    assert facts["f9"] == "missing"


def test_llm_comparison_smoke_run_with_the_fake_model(tmp_path):
    registry = load_registry(API_ROOT / "providers.toml")
    cases = load_cases(CASES_DIR)
    rows, report = run_comparison(cases, ["fake"], "keywords", registry, tmp_path, workers=2)
    assert rows[0]["model"] == "fake"
    assert rows[0]["valid_rate"] == 1.0
    assert rows[0]["recall"] < 0.5  # the fake model only copies complaints
    text = report.read_text(encoding="utf-8")
    assert "## Ranking" in text and "`fake`" in text
    assert (tmp_path / "runs" / "fake" / f"{cases[0].id}.json").exists()
    assert (tmp_path / "runs.csv").exists()


def test_stt_bakeoff_skips_cases_without_audio_and_scores_the_rest(tmp_path):
    case_dir = tmp_path / "cases" / "x"
    shutil.copytree(CASES_DIR / "01-hypertension-uz-mixed", case_dir)
    (case_dir / "audio.webm").write_bytes(b"fake audio")
    shutil.copytree(CASES_DIR / "02-pediatric-arvi-ru", tmp_path / "cases" / "y")  # no audio
    registry = load_registry(API_ROOT / "providers.toml")

    report = run_bakeoff(load_cases(tmp_path / "cases"), ["fake"], registry, tmp_path / "out")

    results = json.loads((tmp_path / "out" / "results.json").read_text())
    assert len(results) == 1 and results[0]["case"] == "01-hypertension-uz-mixed"
    assert 0 < results[0]["wer"] < 1  # the demo transcript overlaps the case partly
    assert "Cases with audio: 1 of 2" in report.read_text()
