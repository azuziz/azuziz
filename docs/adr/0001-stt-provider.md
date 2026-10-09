# ADR 0001: Speech-to-text provider for the pilot

- **Status:** Proposed. Waiting for the bake-off run (needs recordings and API keys).
- **Date:** 2026-10-09

## Context
Consultations mix Uzbek and Russian, often within one sentence. The STT has to handle code-switching, medical
terms (drug names usually said in Russian or Latin), two speakers, and phone microphones in noisy rooms. Audio is
personal data, and its residency is still an open legal question ([02](../02-uzbekistan-context.md) §4.1).

## Candidates
| Provider | Why it's in | Config id |
|---|---|---|
| ElevenLabs Scribe v2 | Best published Uzbek WER among hosted options (15.9% FLEURS for v1); diarization | `elevenlabs` |
| OpenAI transcription | Same vendor as GPT-6 Luna, so one fewer data processor | `openai` |
| Self-hosted GigaAM-Multilingual | Open weights, strong on UZ/RU, can run in Uzbekistan. **Phase 2** (Sprint 8) | — |

## How we decide
Run `python -m scribe.evaluation.stt_bakeoff --providers elevenlabs,openai` on the role-play recordings. Compare
WER per language (uz / ru / mixed), medical-term recall, p50 latency, and price per minute. Record the result here.

## Decision
_Pending._
