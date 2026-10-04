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
Sprint 1 is not started yet. The repo contains the plan only; code arrives with Sprint 1.
