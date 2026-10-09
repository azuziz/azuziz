"""Compare speech-to-text providers on the eval cases that have an audio recording.

Put a consented recording next to a case as `eval/cases/<case>/audio.<webm|m4a|mp3|wav|...>`; its `segments` are
the reference transcript. Audio files are git-ignored.

    python -m scribe.evaluation.stt_bakeoff --providers elevenlabs,openai
"""

import argparse
import json
import logging
import mimetypes
import statistics
import sys
from datetime import datetime
from pathlib import Path

from scribe.evaluation.cases import EvalCase, load_cases
from scribe.evaluation.llm_compare import REPO_ROOT
from scribe.evaluation.text import cer, term_recall, wer
from scribe.providers import Registry, get_registry
from scribe.stt import make_stt

log = logging.getLogger("stt_bakeoff")


def run_bakeoff(cases: list[EvalCase], provider_ids: list[str], registry: Registry, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with_audio = [c for c in cases if c.audio_path]
    results: list[dict] = []
    for pid in provider_ids:
        stt = make_stt(registry.get_stt(pid))
        for case in with_audio:
            mime = mimetypes.guess_type(case.audio_path.name)[0] or "application/octet-stream"
            row = {"provider": pid, "case": case.id, "language": case.conversation_language}
            try:
                res = stt.transcribe(case.audio_path.read_bytes(), case.audio_path.name, mime)
            except Exception as e:  # noqa: BLE001
                log.error("%s on %s failed: %s", pid, case.id, e)
                results.append({**row, "error": f"{type(e).__name__}: {e}"})
                continue
            hyp = res.transcript.text
            results.append(
                {
                    **row,
                    "wer": wer(case.reference_text, hyp),
                    "cer": cer(case.reference_text, hyp),
                    "term_recall": term_recall(case.medical_terms, hyp),
                    "latency_s": res.latency_s,
                    "cost_usd": res.cost_usd,
                    "duration_s": res.transcript.duration_s,
                    "speakers": len({s.speaker for s in res.transcript.segments if s.speaker}),
                    "hypothesis": hyp,
                }
            )
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# STT bake-off — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Cases with audio: {len(with_audio)} of {len(cases)}"
        + ("" if with_audio else " — **add recordings as eval/cases/<case>/audio.***"),
        "",
        "| Provider | WER | CER | Term recall | WER uz | WER ru | WER mixed | p50 latency | $/min | Errors |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for pid in provider_ids:
        ok = [r for r in results if r["provider"] == pid and "error" not in r]
        errs = sum(1 for r in results if r["provider"] == pid and "error" in r)

        costs = [r["cost_usd"] / (r["duration_s"] / 60) for r in ok if r.get("cost_usd") and r.get("duration_s")]
        latency = statistics.median([r["latency_s"] for r in ok]) if ok else 0
        lines.append(
            f"| `{pid}` | {_mean(ok, 'wer')} | {_mean(ok, 'cer')} | {_mean(ok, 'term_recall')} | "
            f"{_mean(ok, 'wer', 'uz')} | {_mean(ok, 'wer', 'ru')} | {_mean(ok, 'wer', 'uz+ru')} | {latency:.1f}s | "
            f"{f'${statistics.fmean(costs):.4f}' if costs else 'n/a'} | {errs} |"
        )
    lines += ["", "Hypotheses per case are in `results.json`.", ""]
    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _mean(rows: list[dict], key: str, language: str | None = None) -> str:
    vals = [r[key] for r in rows if r.get(key) is not None and (language is None or r["language"] == language)]
    return f"{statistics.fmean(vals):.1%}" if vals else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, default=REPO_ROOT / "eval" / "cases")
    parser.add_argument("--providers", default="elevenlabs,openai")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    registry = get_registry()
    provider_ids = [p.strip() for p in args.providers.split(",") if p.strip()]
    missing = [p for p in provider_ids if not registry.get_stt(p).has_key()]
    if missing:
        for p in missing:
            log.error("No API key for %s: set %s", p, registry.get_stt(p).api_key_env)
        return 2
    out_dir = args.out or REPO_ROOT / "eval" / "reports" / f"stt-{datetime.now():%Y%m%d-%H%M%S}"
    report = run_bakeoff(load_cases(args.cases), provider_ids, registry, out_dir)
    print(report.read_text(encoding="utf-8"))
    print(f"\nReport: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
