# Sprint 1: walking skeleton ("record a consultation and get a note")

**Sprint goal:** a doctor opens a URL on a phone or laptop, records a role-played consultation in Uzbek, Russian or a
mix, and in about 1 minute gets a structured outpatient note in the language they pick.

**Friday demo script:** the clinical lead and a colleague role-play a 5-minute therapist visit (hypertension follow-up)
in Uzbek with Russian drug names. They press stop, see the note and copy it. We show the WER and cost-per-note numbers
from the eval run.

## Stories

| # | Story | Acceptance criteria | Est. |
|---|---|---|---|
| 1 | As a dev, I have a monorepo with CI and a staging deploy | `apps/web` and `apps/api` scaffolded · lint and tests run in GitHub Actions · `docker compose up` runs everything locally · staging URL reachable | 0.75 d |
| 2 | As a doctor, I can record a consultation in the browser | Start/stop button and timer · works in Chrome on Android, Safari on iOS and desktop · audio uploaded and stored (encrypted) · recordings of 30 min and longer work | 0.75 d |
| 3 | As the PO, I know which STT is best for us | **Bake-off**: 2–3 providers on 5 recordings (UZ, RU, mixed) · WER, medical-term recall, latency, price per minute in a table · decision recorded in `docs/adr/0001-stt-provider.md` | 0.75 d |
| 4 | As a doctor, I get a transcript | STT adapter interface plus the winning provider · transcript with timestamps and language tags · retry on failure | 0.5 d |
| 5 | As a doctor, I get a structured note | Claude (`claude-opus-5-5`) with structured output matching the note schema (`docs/04-architecture.md`) · CIS outpatient sections · output language `uz-Latn` or `ru` · fields that weren't said go to `not_mentioned` · note rendered in the UI with a copy button | 1.25 d |
| 6 | As the team, we can measure quality and cost | `eval/` with 10 role-play recordings plus reference transcripts and notes · a script that computes WER per language and a note-field checklist score · cost and latency logged per note | 0.75 d |
| 7 | As the PO, I see one-page docs for how to run and deploy | README "Getting started" · `.env.example` · no secrets in git | 0.25 d |

**Total: about 5 ideal days.**

## Inputs needed from you this week
1. **API keys:** Anthropic, plus STT candidates for the bake-off (e.g. ElevenLabs). Store them as environment secrets and never commit them.
2. **Hosting for staging:** any VM is fine in Sprint 1. The production location in UZ is decided by Sprint 6.
3. **5 role-play recordings by Wednesday** (UZ, RU, mixed; 3–10 min each) with written consent from the people speaking.
   No real patients in Sprint 1.
4. **15 minutes with a doctor** to check that the section names and order of the note template match how they write.
5. Confirm the **stack** (Python/FastAPI and Next.js), or tell us your preference.

## Out of scope this sprint
Login, patient records, real-time streaming, Telegram, templates by specialty. These are Sprints 2–5.
