"""Compare LLMs on the eval cases: same reference transcript in, structured note out, graded and costed.

    python -m scribe.evaluation.llm_compare                      # all 4 candidates, GPT-6 Sol as judge
    python -m scribe.evaluation.llm_compare --models gpt-6-luna,or/kimi-k3 --judge keywords

Method and decision rule: docs/05-llm-comparison.md.
"""

import argparse
import csv
import json
import logging
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from scribe.config import API_ROOT
from scribe.evaluation.cases import EvalCase, load_cases
from scribe.evaluation.judge import Grade, keyword_grade, llm_grade
from scribe.evaluation.text import wrong_script_ratio
from scribe.llm.client import ChatClient, make_client
from scribe.notes.generator import NoteGenerationError, generate_note
from scribe.notes.schema import Note, render_text
from scribe.providers import Registry, get_registry

log = logging.getLogger("llm_compare")
REPO_ROOT = API_ROOT.parents[1]
DEFAULT_MODELS = "gpt-6-luna,mimo-v2.6-pro,kimi-k2.6,kimi-k3"
WEIGHTS = {"recall": 0.35, "hallucination": 0.25, "script": 0.20, "icd": 0.05, "latency": 0.05, "cost": 0.10}
NOTES_PER_DOCTOR_MONTH = 300


@dataclass
class Run:
    model: str
    case: str
    ok: bool
    error: str | None = None
    attempts: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    recall: float = 0.0
    keyword_recall: float = 0.0
    critical: int = 0
    major: int = 0
    minor: int = 0
    critical_errors: int = 0
    critical_omissions: int = 0
    wrong_script: float = 0.0
    icd: float | None = None
    judge_cost_usd: float = 0.0

    @property
    def hallucination_score(self) -> float:
        if not self.ok:
            return 0.0
        return max(0.0, 1.0 - (self.critical * 1.0 + self.major * 0.5 + self.minor * 0.1))

    @property
    def script_score(self) -> float:
        if not self.ok:
            return 0.0
        return 1.0 if self.wrong_script <= 0.02 else max(0.0, 1 - (self.wrong_script - 0.02) / 0.18)


def icd_score(case: EvalCase, note: Note) -> float | None:
    if not case.expected_icd10:
        return None
    codes = {(d.icd10 or "").upper().strip() for d in note.diagnoses if d.kind == "main"} or {
        (d.icd10 or "").upper().strip() for d in note.diagnoses
    }
    if codes & {c.upper() for c in case.expected_icd10}:
        return 1.0
    if codes & {c.upper() for c in case.acceptable_icd10}:
        return 0.5
    return 0.0


def evaluate_one(client: ChatClient, judge: ChatClient | None, case: EvalCase, max_retries: int, out_dir: Path) -> Run:
    record: dict = {"model": client.spec.id, "case": case.id}
    try:
        result = generate_note(client, case.transcript(), case.output_language, case.specialty, max_retries)
    except NoteGenerationError as e:
        run = Run(model=client.spec.id, case=case.id, ok=False, error=str(e), attempts=e.attempts)
        run.cost_usd = e.usage.cost_usd(client.spec)
        _save(out_dir, run, {**record, "error": str(e)})
        return run
    except Exception as e:  # noqa: BLE001 - network/auth errors are reported per run, not fatal
        log.error("%s on %s failed: %s", client.spec.id, case.id, e)
        run = Run(model=client.spec.id, case=case.id, ok=False, error=f"{type(e).__name__}: {e}")
        _save(out_dir, run, {**record, "error": run.error})
        return run

    text = render_text(result.note, case.output_language)
    kw = keyword_grade(case, result.note)
    grade: Grade = kw
    judge_error = None
    if judge is not None:
        try:
            grade = llm_grade(judge, case, text)
        except Exception as e:  # noqa: BLE001
            judge_error = f"{type(e).__name__}: {e}"
            log.error("judge failed on %s/%s: %s", client.spec.id, case.id, e)

    run = Run(
        model=client.spec.id,
        case=case.id,
        ok=True,
        attempts=result.attempts,
        latency_s=result.usage.latency_s,
        cost_usd=result.cost_usd,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        recall=grade.recall(),
        keyword_recall=kw.recall(),
        critical=grade.count("critical"),
        major=grade.count("major"),
        minor=grade.count("minor"),
        critical_errors=grade.critical_errors(case),
        critical_omissions=grade.critical_omissions(case),
        wrong_script=wrong_script_ratio(text, case.output_language),
        icd=icd_score(case, result.note),
        judge_cost_usd=grade.usage.cost_usd(judge.spec) if judge is not None and grade.judge != "keywords" else 0.0,
    )
    _save(
        out_dir,
        run,
        {
            **record,
            "note": result.note.model_dump(),
            "text": text,
            "metrics": result.metrics(),
            "grade": {"judge": grade.judge, "facts": grade.facts, "unsupported": grade.unsupported},
            "keyword_facts": kw.facts,
            "judge_error": judge_error,
        },
    )
    return run


def _save(out_dir: Path, run: Run, payload: dict) -> None:
    path = out_dir / "runs" / run.model.replace("/", "__") / f"{run.case}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _p(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[int(q * 100) - 1]


def summarize(runs: list[Run], models: list[str]) -> list[dict]:
    rows = []
    for model in models:
        rs = [r for r in runs if r.model == model]
        ok = [r for r in rs if r.ok]
        icds = [r.icd for r in ok if r.icd is not None]
        latencies = [r.latency_s for r in ok]
        rows.append(
            {
                "model": model,
                "cases": len(rs),
                "valid_rate": len(ok) / len(rs) if rs else 0.0,
                "first_try_rate": sum(r.attempts == 1 for r in ok) / len(rs) if rs else 0.0,
                "recall": statistics.fmean(r.recall for r in rs) if rs else 0.0,
                "keyword_recall": statistics.fmean(r.keyword_recall for r in rs) if rs else 0.0,
                "hallucination_score": statistics.fmean(r.hallucination_score for r in rs) if rs else 0.0,
                "script_score": statistics.fmean(r.script_score for r in rs) if rs else 0.0,
                "icd": statistics.fmean(icds) if icds else 0.0,
                "critical_errors": sum(r.critical_errors for r in rs),
                "critical_omissions": sum(r.critical_omissions for r in rs),
                "major": sum(r.major for r in rs),
                "minor": sum(r.minor for r in rs),
                "latency_p50": _p(latencies, 0.5),
                "latency_p95": _p(latencies, 0.95),
                "cost_per_note": statistics.fmean(r.cost_usd for r in ok) if ok else 0.0,
                "judge_cost": sum(r.judge_cost_usd for r in rs),
                "errors": [r.error for r in rs if r.error],
            }
        )
    valid = [r for r in rows if r["valid_rate"] > 0]
    best_latency = min((r["latency_p50"] for r in valid if r["latency_p50"] > 0), default=0.0)
    best_cost = min((r["cost_per_note"] for r in valid if r["cost_per_note"] > 0), default=0.0)
    for r in rows:
        r["latency_score"] = (best_latency / r["latency_p50"]) if r["latency_p50"] > 0 else float(r["valid_rate"] > 0)
        r["cost_score"] = (best_cost / r["cost_per_note"]) if r["cost_per_note"] > 0 else float(r["valid_rate"] > 0)
        r["cost_per_doctor_month"] = r["cost_per_note"] * NOTES_PER_DOCTOR_MONTH
        r["score"] = (
            WEIGHTS["recall"] * r["recall"]
            + WEIGHTS["hallucination"] * r["hallucination_score"]
            + WEIGHTS["script"] * r["script_score"]
            + WEIGHTS["icd"] * r["icd"]
            + WEIGHTS["latency"] * r["latency_score"]
            + WEIGHTS["cost"] * r["cost_score"]
        )
        reasons = []
        if r["critical_errors"]:
            reasons.append(f"{r['critical_errors']} critical drug/dose/allergy error(s)")
        if r["valid_rate"] < 0.98:
            reasons.append(f"valid notes {r['valid_rate']:.0%} < 98%")
        r["disqualified"] = "; ".join(reasons)
    rows.sort(key=lambda r: (bool(r["disqualified"]), -r["score"]))
    return rows


def write_report(out_dir: Path, cases: list[EvalCase], runs: list[Run], rows: list[dict], judge_id: str) -> Path:
    with (out_dir / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [k for k in Run.__dataclass_fields__] + ["hallucination_score", "script_score"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in runs:
            w.writerow(
                {
                    **{k: getattr(r, k) for k in Run.__dataclass_fields__},
                    **{"hallucination_score": r.hallucination_score, "script_score": r.script_score},
                }
            )

    synthetic = sum(c.synthetic for c in cases)
    lines = [
        f"# LLM comparison — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Cases: {len(cases)} ({synthetic} synthetic)"
        + (" — **synthetic cases still need clinical review**" if synthetic else ""),
        f"- Judge: `{judge_id}`"
        + (" (keyword matching only: cannot detect hallucinations)" if judge_id == "keywords" else ""),
        f"- Weights: {', '.join(f'{k} {v:.0%}' for k, v in WEIGHTS.items())}. Method: docs/05-llm-comparison.md",
        "",
        "## Ranking",
        "",
        "| # | Model | Score | Recall | Halluc. score | Script | ICD-10 | Critical errors | Valid | p50 latency "
        "| $/note | $/doctor-month | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        status = f"❌ {r['disqualified']}" if r["disqualified"] else "✅"
        lines.append(
            f"| {i} | `{r['model']}` | {r['score']:.3f} | {r['recall']:.0%} | {r['hallucination_score']:.2f} | "
            f"{r['script_score']:.2f} | {r['icd']:.0%} | {r['critical_errors']} | {r['valid_rate']:.0%} | "
            f"{r['latency_p50']:.1f}s | ${r['cost_per_note']:.4f} | ${r['cost_per_doctor_month']:.2f} | {status} |"
        )
    lines += [
        "",
        "## Details",
        "",
        "| Model | Keyword recall | Critical omissions | Major | Minor | First-try valid | p95 latency | Judge $ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['model']}` | {r['keyword_recall']:.0%} | {r['critical_omissions']} | {r['major']} | {r['minor']} | "
            f"{r['first_try_rate']:.0%} | {r['latency_p95']:.1f}s | ${r['judge_cost']:.4f} |"
        )
    models = [r["model"] for r in rows]
    lines += [
        "",
        "## Per case (recall / critical errors)",
        "",
        "| Case | " + " | ".join(f"`{m}`" for m in models) + " |",
        "|---|" + "---|" * len(models),
    ]
    for c in cases:
        cells = []
        for m in models:
            run = next((x for x in runs if x.model == m and x.case == c.id), None)
            cells.append(
                "—" if run is None else ("error" if not run.ok else f"{run.recall:.0%} / {run.critical_errors}")
            )
        lines.append(f"| {c.id} | " + " | ".join(cells) + " |")
    errors = [(r["model"], e) for r in rows for e in r["errors"]]
    if errors:
        lines += ["", "## Errors", ""] + [f"- `{m}`: {e[:300]}" for m, e in errors]
    lines += ["", "Notes and grades for every run are in `runs/<model>/<case>.json`.", ""]
    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_comparison(
    cases: list[EvalCase],
    model_ids: list[str],
    judge_id: str,
    registry: Registry,
    out_dir: Path,
    workers: int = 4,
    max_retries: int = 1,
) -> tuple[list[dict], Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    clients = {m: make_client(registry.get_llm(m)) for m in model_ids}
    judge = None if judge_id == "keywords" else make_client(registry.get_llm(judge_id))
    if judge is not None and judge.spec.provider == "fake":
        judge = None  # the fake model can't grade; fall back to keywords
        judge_id = "keywords"
    jobs = [(clients[m], c) for m in model_ids for c in cases]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        runs = list(pool.map(lambda job: evaluate_one(job[0], judge, job[1], max_retries, out_dir), jobs))
    rows = summarize(runs, model_ids)
    (out_dir / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows, write_report(out_dir, cases, runs, rows, judge_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, default=REPO_ROOT / "eval" / "cases")
    parser.add_argument("--only", help="comma-separated case ids")
    parser.add_argument(
        "--models", default=DEFAULT_MODELS, help=f"comma-separated model ids (default {DEFAULT_MODELS})"
    )
    parser.add_argument("--judge", default="gpt-6-sol", help="judge model id, or 'keywords' for no LLM judge")
    parser.add_argument("--out", type=Path, default=None, help="report directory (default eval/reports/<timestamp>)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-retries", type=int, default=1)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    registry = get_registry()
    model_ids = [m.strip() for m in args.models.split(",") if m.strip()]
    missing = [
        m for m in model_ids + ([args.judge] if args.judge != "keywords" else []) if not registry.get_llm(m).has_key()
    ]
    if missing:
        for m in missing:
            log.error("No API key for %s: set %s", m, registry.get_llm(m).api_key_env)
        return 2
    cases = load_cases(args.cases, args.only.split(",") if args.only else None)
    if not cases:
        log.error("No cases found in %s", args.cases)
        return 2
    out_dir = args.out or REPO_ROOT / "eval" / "reports" / f"llm-{datetime.now():%Y%m%d-%H%M%S}"
    rows, report = run_comparison(cases, model_ids, args.judge, registry, out_dir, args.workers, args.max_retries)
    print(report.read_text(encoding="utf-8"))
    print(f"\nReport: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
