# azuziz: AI clinical assistant for Uzbekistan

An AI scribe and clinical copilot for doctors and clinics in Uzbekistan, working in **Uzbek (Latin and Cyrillic) and
Russian**. It is modeled on what [Telepatía AI](docs/01-telepatia-analysis.md) built for Latin America, and adapted to Uzbekistan's
languages, note formats, national e-health systems (DMED / DHP) and regulation.

**What the doctor gets:** they talk with the patient as usual, and a structured, editable medical note is ready when
the patient leaves. Later releases add safety alerts with sources, 100% note auditing, and an AI care team.

## Plan
| Doc | What's inside |
|---|---|
| [01 · Telepatía teardown](docs/01-telepatia-analysis.md) | What they do, their modules, traction, business model, and lessons |
| [02 · Uzbekistan context](docs/02-uzbekistan-context.md) | Market, language reality, speech tech, regulation, unit economics |
| [03 · Roadmap](docs/03-roadmap.md) | Phases, a weekly sprint plan, time estimates, KPIs, risks |
| [04 · Architecture](docs/04-architecture.md) | Stack, data flow, note schema, privacy checklist |
| [05 · LLM comparison](docs/05-llm-comparison.md) | GPT-6 Luna vs MiMo-V2.6-Pro vs Kimi: prices, cost per note, data-transfer rules, test method |
| [Sprint 1](docs/sprints/sprint-01.md) | This week's backlog |

## Releases (nominal)
| Week | Release |
|---|---|
| 6 | **v1.0 Pilot**: AI Scribe (web and Telegram, UZ/RU) |
| 10 | v1.5: our own Uzbek/Russian medical ASR |
| 15 | **v2.0 Clinic**: organizations, patient context, FHIR/DMED, billing |
| 21 | **v3.0 Copilot**: CDSS with Uzbek MoH protocols and drug safety |
| 25 | **v4.0 Audit**: 100% note auditing, quality dashboards |
| 35 | v5.x: AI intake nurse, follow-up agent, inpatient workflows |

## Status
**Sprint 1, walking skeleton.** A doctor records a consultation in the browser and gets a structured note in Uzbek
(Latin or Cyrillic) or Russian. A test harness compares GPT-6 Luna, MiMo-V2.6-Pro and Kimi on the same transcripts.
Story-by-story status is in [sprint-01.md](docs/sprints/sprint-01.md).

## Getting started

```
apps/api/    FastAPI service: recording upload, STT, LLM note drafting, evaluation scripts (Python 3.11+)
apps/web/    Next.js web app: recorder and note review (Node 22)
eval/cases/  test consultations used to compare models (see eval/README.md)
```

**1. API**
```bash
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # add keys; without any it runs in demo mode with fake providers
uvicorn --factory scribe.main:app_factory --reload --port 8000
```

**2. Web app** (in a second terminal)
```bash
cd apps/web
npm install
npm run dev                     # http://localhost:3000
```

Or run both with Docker: `docker compose up --build`.

**3. Use real providers.** In `apps/api/.env`, set the keys you have and choose the defaults, for example:
```bash
OPENAI_API_KEY=...       # GPT-6 Luna (and GPT-6 Sol as the comparison judge)
MIMO_API_KEY=...         # Xiaomi MiMo
MOONSHOT_API_KEY=...     # Kimi
OPENROUTER_API_KEY=...   # MiMo and Kimi through one key: models "or/mimo-v2.6-pro", "or/kimi-k2.6", "or/kimi-k3"
ELEVENLABS_API_KEY=...   # speech recognition
STT_PROVIDER=elevenlabs
LLM_MODEL=gpt-6-luna
```
Model IDs, base URLs and prices live in [`apps/api/providers.toml`](apps/api/providers.toml).

**4. Compare models**
```bash
cd apps/api && . .venv/bin/activate
python -m scribe.evaluation.llm_compare                                  # 4 candidates, GPT-6 Sol as judge
python -m scribe.evaluation.llm_compare --models or/mimo-v2.6-pro,or/kimi-k2.6 --judge keywords
python -m scribe.evaluation.stt_bakeoff --providers elevenlabs,openai   # needs recordings in eval/cases
```
Reports are written to `eval/reports/`.

**5. Checks** (CI runs the same)
```bash
cd apps/api && ruff check . && ruff format --check . && pytest -q
cd apps/web && npm run typecheck && npm run build
```
