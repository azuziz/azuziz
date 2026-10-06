# Architecture (v1, to be refined each sprint)

## Principles
1. **Modular monolith first.** One API service plus one worker. We split services only when load or teams require it.
2. **Provider-agnostic AI.** STT and LLM sit behind adapters, so we can swap vendors or self-host without a rewrite.
3. **Structured-first.** Notes are versioned JSON with evidence spans, aligned with FHIR R5 (the DHP IG). Text is just one rendering.
4. **Privacy by design.** Audio and PII stay in Uzbekistan, only de-identified text reaches the LLM, and every access is audited.
5. **Eval-driven.** Every change to a prompt, model or STT setting runs against the eval set in CI.

## Stack (recommendation)

| Layer | Choice | Why |
|---|---|---|
| Web app | **Next.js (TypeScript)** as a PWA, Tailwind, i18n for `uz-Latn` / `uz-Cyrl` / `ru` | Runs on any phone or laptop browser with nothing to install, like Telepatía |
| Recording | MediaRecorder or AudioWorklet, Opus codec, chunked upload with an IndexedDB buffer | Works on unstable connections |
| API | **Python 3.12 + FastAPI**, Pydantic, SQLAlchemy + Alembic | Python is the home of the speech and ML ecosystem (fine-tuning, self-hosted ASR) |
| Worker | arq or Celery on Redis | STT and LLM jobs, retries |
| Database | **PostgreSQL 16** (pgvector later for the CDSS knowledge base) | One reliable store |
| Object storage | S3-compatible: MinIO in dev, UzCloud S3 in prod | Audio stays in UZ |
| LLM | **One OpenAI-compatible adapter** (`openai` Python SDK with a per-provider base URL, model ID and key). Candidates: **GPT-6 Luna, MiMo-V2.6-Pro, Kimi K2.6 / K3**. JSON-schema output where supported, JSON mode plus our own validation and retry elsewhere (MiMo). Prompt caching via a stable prompt prefix | The winner comes from the bake-off ([05](05-llm-comparison.md)). The runner-up is the automatic fallback. Switching is a config change |
| STT | Adapter, hosted at first (Sprint 1 bake-off, e.g. ElevenLabs Scribe), then **self-hosted GigaAM-Multilingual** on a GPU in UZ (Phase 2) | Quality, residency, cost |
| Telegram | aiogram bot | Uzbekistan's main messenger |
| Infra | Docker Compose for dev; VMs in a UZ data center for prod; GitHub Actions CI; Sentry | Simple to start |

## Data flow

```mermaid
flowchart LR
  A[Doctor: browser PWA or Telegram] -->|audio chunks, TLS| B(API · FastAPI)
  B --> C[(Object storage · UZ<br/>audio, encrypted)]
  B --> Q[[Job queue]]
  Q --> D[STT worker<br/>hosted → self-hosted in UZ]
  D --> E[Transcript<br/>segments · speaker · lang · timestamps]
  E --> F[De-identification<br/>names, PINFL, phones → tokens]
  F --> G[LLM note builder<br/>adapter: Luna · MiMo · Kimi<br/>primary + fallback]
  G --> H[Validation<br/>schema · ICD-10 · units · evidence spans]
  H --> I[(PostgreSQL · UZ<br/>versioned notes)]
  I --> J[Doctor review & sign]
  J --> K[Outputs: PDF · patient summary ·<br/>FHIR R5 · DMED · browser extension]
```

## Core entities
`Organization` · `User` (doctor, nurse, admin, auditor) · `Patient` (optional in the MVP) · `Encounter` · `AudioRecording`
· `Transcript` (segments: speaker, language, start/end, text) · `Note` (versioned sections, status `draft|signed`,
output language) · `Template` · `Feedback` · `AuditEvent` · `ConsentRecord`

## Note schema (MVP, simplified)

```json
{
  "language": "uz-Latn",
  "specialty": "therapist",
  "sections": {
    "complaints":          {"text": "...", "evidence": [[12.4, 31.0]]},
    "history_present":     {"text": "...", "evidence": [[31.0, 95.2]]},
    "history_life":        {"text": "...", "allergies": ["..."], "evidence": []},
    "objective":           {"text": "...", "vitals": {"bp": "130/85", "hr": 78, "temp_c": 36.8}},
    "diagnosis":           [{"text": "...", "icd10": "I11.9", "type": "main"}],
    "workup_plan":         [{"text": "...", "loinc": null}],
    "treatment":           [{"drug_inn": "amlodipine", "trade_name": "...", "dose": "5 mg", "route": "PO", "frequency": "1×/day", "duration": "30 days"}],
    "recommendations":     "...",
    "follow_up":           "in 2 weeks"
  },
  "not_mentioned": ["history_life.heredity"],
  "ai_generated": true,
  "signed_by": null
}
```

Every field carries **evidence** (timestamps in the transcript). The UI highlights the source when the doctor taps a
sentence. If something wasn't said, it goes in `not_mentioned` and is never invented.

## Security and privacy checklist (part of the Definition of Done)
- [ ] TLS everywhere, encryption at rest (DB and object storage), secrets in an env or secret manager, never in git
- [ ] Per-tenant isolation in every query, RBAC
- [ ] `AuditEvent` written on every read or write of clinical data
- [ ] De-identification before any third-party AI call, and re-identification only on our side
- [ ] Configurable audio retention (default: delete after transcript verification + N days)
- [ ] A consent record exists before recording starts
- [ ] Notes labeled as AI drafts until signed
- [ ] Real patient data goes only to an LLM provider or host in an approved jurisdiction (see [05](05-llm-comparison.md) §3), with zero data retention requested and no training on our data
- [ ] The bake-off and development use only role-play or synthetic data

## Proposed repo layout
```
apps/web/          Next.js PWA (doctor UI)
apps/api/          FastAPI service and worker
apps/telegram/     Telegram bot (Sprint 5)
packages/schema/   Note JSON schema and FHIR mappings, shared by api and web
eval/              Eval recordings (consented and de-identified, outside git), references, scripts, reports
infra/             docker-compose, deployment
docs/              this plan, ADRs, sprint notes
```
