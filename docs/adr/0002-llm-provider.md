# ADR 0002: LLM for note drafting

- **Status:** Proposed. Waiting for the first comparison run (needs API keys).
- **Date:** 2026-10-09

## Context
The team chose to compare Kimi, MiMo-V2.6-Pro and GPT Luna on price and quality. Prices, data-transfer constraints
and the test method are in [05 · LLM comparison](../05-llm-comparison.md).

## Candidates
`gpt-6-luna`, `mimo-v2.6-pro`, `kimi-k2.6`, `kimi-k3` (or the `or/...` OpenRouter variants). Judge: `gpt-6-sol`.

## How we decide
```bash
python -m scribe.evaluation.llm_compare            # writes eval/reports/llm-<timestamp>/report.md
```
1. Drop any model with a critical drug, dose or allergy error, or less than 98% valid notes.
2. Rank the rest by weighted score.
3. The clinical lead does a blind side-by-side review of the top 2.
4. The winner becomes `LLM_MODEL` for the pilot; the runner-up is the fallback.

## Results
| Run | Cases | Winner | Runner-up | Notes |
|---|---|---|---|---|
| _pending_ | | | | |

## Decision
_Pending._ Before any real patient data, the chosen provider or host must also pass the data-transfer check in
[05](../05-llm-comparison.md) §3.
