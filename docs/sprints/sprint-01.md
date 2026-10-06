# Sprint 1: walking skeleton ("record a consultation and get a note")

**Sprint goal:** a doctor opens a URL on a phone or laptop, records a role-played consultation in Uzbek, Russian or a
mix, and in about 1 minute gets a structured outpatient note in the language they pick.

**Friday demo script:** the clinical lead and a colleague role-play a 5-minute therapist visit (hypertension follow-up)
in Uzbek with Russian drug names. They press stop, see the note and copy it. Then we show the 4 models' notes for
the same transcript side by side, with the quality, latency and cost-per-note table from the eval run.

## Stories

| # | Story | Acceptance criteria | Est. |
|---|---|---|---|
| 1 | As a dev, I have a monorepo with CI and a staging deploy | `apps/web` and `apps/api` scaffolded · lint and tests run in GitHub Actions · `docker compose up` runs everything locally · staging URL reachable | 0.75 d |
| 2 | As a doctor, I can record a consultation in the browser | Start/stop button and timer · works in Chrome on Android, Safari on iOS and desktop · audio uploaded and stored (encrypted) · recordings of 30 min and longer work | 0.75 d |
| 3 | As the PO, I know which STT is best for us | **Bake-off**: 2–3 providers on 5 recordings (UZ, RU, mixed) · WER, medical-term recall, latency, price per minute in a table · decision recorded in `docs/adr/0001-stt-provider.md` | 0.75 d |
| 4 | As a doctor, I get a transcript | STT adapter interface plus the winning provider · transcript with timestamps and language tags · retry on failure | 0.5 d |
| 5 | As a doctor, I get a structured note | OpenAI-compatible LLM adapter with 4 configured models (GPT-6 Luna, MiMo-V2.6-Pro, Kimi K2.6, Kimi K3), chosen by config · output validated against the note schema (`docs/04-architecture.md`), with one retry on invalid JSON · CIS outpatient sections · output language `uz-Latn` or `ru` · fields that weren't said go to `not_mentioned` · note rendered in the UI with a copy button | 1.0 d |
| 6 | As the team, we know which LLM is best and what it costs | `eval/` with 10 role-play recordings plus reference transcripts, gold notes and key-fact lists · WER per language · **LLM comparison run: the same 10 transcripts through all 4 models**, scoring schema validity, key-fact recall, hallucinations (critical: drugs, doses, allergies), script correctness, latency and real cost · report in `eval/reports/` · preliminary pick recorded in `docs/adr/0002-llm-provider.md` (method in [05](../05-llm-comparison.md)) | 1.0 d |
| 7 | As the PO, I see one-page docs for how to run and deploy | README "Getting started" · `.env.example` · no secrets in git | 0.25 d |

**Total: about 5 ideal days.**

## Inputs needed from you this week
1. **API keys:** OpenAI (GPT-6 Luna), Xiaomi MiMo, Moonshot (Kimi), plus STT candidates for the bake-off (e.g.
   ElevenLabs). A single OpenRouter key can stand in for MiMo and Kimi during the bake-off. Store keys as environment
   secrets and never commit them. Budget: the whole 4-model comparison costs well under USD 5.
2. **Hosting for staging:** any VM is fine in Sprint 1. The production location in UZ is decided by Sprint 6.
3. **5 role-play recordings by Wednesday** (UZ, RU, mixed; 3–10 min each) with written consent from the people speaking.
   No real patients in Sprint 1.
4. **15 minutes with a doctor** to check that the section names and order of the note template match how they write.
5. Confirm the **stack** (Python/FastAPI and Next.js), or tell us your preference.

## Out of scope this sprint
Login, patient records, real-time streaming, Telegram, templates by specialty. These are Sprints 2–5.
