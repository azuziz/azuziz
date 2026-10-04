# Roadmap: weekly sprints, a working product every Friday

## 0. How we work

**Team assumptions.** The estimates below depend on these.

| Role | Who | Load |
|---|---|---|
| Product Owner and developer | You | Full-time |
| Pair engineer (writes most code, tests and docs; runs research and evals) | Claude | Every working session |
| **Clinical lead** (a practicing doctor who validates templates and notes, and later protocols) | To recruit in week 1 | 4–6 h/week. **Mandatory** |
| Design-partner doctors | 3–5 by Sprint 3, 5–10 at pilot, 20–30 by Sprint 10 | Use the product and give feedback |
| Local legal counsel | Fixed-scope engagement | Weeks 1–6, then again around weeks 14–20 |
| +1 engineer (full-stack or ML) | Recommended from Phase 3 | Full-time |
| Sales and partnerships | Recommended from Phase 3 | Full-time |

**Cadence (1-week sprints):**
- **Monday:** sprint planning (30 min). Pick stories from this roadmap and write `docs/sprints/sprint-NN.md`.
- **Daily:** build, test, deploy to staging.
- **Friday:** **demo the working increment** to the clinical lead and design partners, collect feedback, hold a retro and update this roadmap.
- **Definition of Done:** deployed to staging (and to production once the pilot starts in Sprint 6), unit tests pass, the
  eval regression suite shows no drop, the privacy checklist passes, the change is documented and has been demoed.

**Estimate scale:** each sprint holds about 5 ideal days of work for the core pair. Calendar estimates add a **25% buffer**
because of external dependencies (DMED access, legal opinions, licensed drug data, doctor availability).

---

## 1. Phases at a glance

| Phase | Sprints | Release | Telepatía equivalent | Nominal end | Realistic (+25%) |
|---|---|---|---|---|---|
| **1. MVP AI Scribe** | S1–S6 | **v1.0 Pilot** | AI Scribe | Week 6 | Weeks 7–8 |
| **2. Speech quality and our own ASR** | S7–S10 | v1.5 | (localization moat) | Week 10 | Weeks 12–13 |
| **3. Clinic platform and integrations** | S11–S15 | **v2.0 Clinic** | Enterprise and EHR integration | Week 15 | ~Month 4–5 |
| **4. Clinical copilot (CDSS)** | S16–S21 | **v3.0 Copilot** | AI CDSS | Week 21 | ~Month 6–6.5 |
| **5. Audit and quality analytics** | S22–S25 | **v4.0 Audit** | Note auditing | Week 25 | ~Month 7–8 |
| **6. AI care team and expansion** | S26–S35 | v5.x | AI nurses, doctors, auditors | Week 35 | ~Month 9–10 |

**Bottom line:**
- **A usable scribe for real doctors: about 6 weeks.**
- **A clinic-ready paid product: about 4 months.**
- **Parity with Telepatía's core (scribe, CDSS and audit): about 6 months nominal, 7–8 months realistic.**

---

## 2. Phase 1: MVP AI Scribe (Sprints 1–6)

> Goal: a doctor in Tashkent records a real Uzbek/Russian consultation and gets a correct, structured,
> editable note within a minute, on the phone or laptop they already own.

| Sprint | Goal | Key stories | Friday demo |
|---|---|---|---|
| **S1** | **Walking skeleton: record a consultation and get a note** | Repo, CI and staging deploy · in-browser recorder · ASR adapter plus a 1-day **STT bake-off** (5 UZ/RU/mixed recordings) · Claude note generator with structured output (CIS outpatient schema) · note view and copy · eval harness v0 (10 role-plays, WER) · cost and latency logging. Details in [sprint-01.md](sprints/sprint-01.md) | Live role-played consultation in Uzbek with Russian terms produces a structured note |
| **S2** | **A doctor can actually use it** | Phone OTP login (local SMS gateway) · encounter list · section-by-section note editor with "regenerate section" · output language switch `uz-Latn` / `uz-Cyrl` / `ru` with deterministic transliteration · UI in UZ and RU · PDF/print export · consent checkbox | The clinical lead runs 3 role-plays end to end on their own phone |
| **S3** | **Real-time and robust** | Streaming transcription over WebSocket with live transcript · chunked upload with local buffering (IndexedDB) that survives network drops · speaker diarization (doctor/patient) · pause/resume, consultations up to 60 min · Opus-codec audio at low bitrate | A 20-min consultation with Wi-Fi switched off mid-way loses nothing, and the note arrives in under 45 s |
| **S4** | **Specialties and medical vocabulary** | Templates for 6 specialties (GP/therapist, pediatrics, cardiology, OB/GYN, neurology, dentistry), validated by the clinical lead · custom templates · **ICD-10 suggestions** (RU and UZ names) · drug dictionary from the Uzbek state register, used for STT boosting and LLM correction · eval set grows to 30 recordings with per-language WER and term recall | Cardiology and pediatrics consultations produce specialty-shaped notes with ICD-10 codes |
| **S5** | **Telegram and patient-facing outputs** | **Telegram bot**: send a voice note or audio file and get the note back with an edit link · Telegram login · **patient summary** in the patient's language, sent by Telegram or SMS or printed · referral letter and recommendations sheet · dictation mode (post-visit monologue) | A doctor forwards a voice note in Telegram and gets the note in about a minute; the patient gets a plain-Uzbek summary |
| **S6** | **Pilot readiness → v1.0** | Encryption at rest, audit log of every access, RBAC basics · **de-identification layer before the LLM** · audio retention policy (auto-delete) and deletion on request · audio hosted in UZ · observability (errors, latency, cost per note) · in-app feedback (1–5 rating, edit-distance tracking) · onboarding in UZ and RU, landing page | **v1.0 Pilot launch with 5–10 doctors** |

**Phase 1 exit criteria (KPIs):**
- ≥70% of notes accepted with minor edits (<20% of characters changed)
- Doctor rating ≥4/5
- p50 time from "stop" to note <45 s
- WER on our eval set: UZ ≤20%, RU ≤10%
- Zero privacy incidents

---

## 3. Phase 2: speech quality and our own ASR (Sprints 7–10)

| Sprint | Goal | Key stories |
|---|---|---|
| **S7** | **Measure what doctors change** | Analytics on edits (which sections, which error types) · weekly quality review with the clinical lead · note-quality rubric (completeness, hallucination, correctness, style) graded by an LLM judge and spot-checked by doctors · eval regression gate in CI · **model decision**: compare Opus 5.5, Sonnet 5.5 and Haiku 4.5 on our eval for quality vs. cost |
| **S8** | **Self-hosted ASR v1 in Uzbekistan** | Deploy GigaAM-Multilingual (or the bake-off winner) on a GPU in UZ · ASR router choosing a provider by language, quality and cost · A/B test against hosted STT |
| **S9** | **Medical domain adaptation** | Fine-tune on consented, de-identified pilot audio plus role-play recordings for UZ↔RU medical code-switching · hotword boosting for drugs and dosages · post-ASR LLM correction of drug names and units |
| **S10** | **Personalization and speed → v1.5** | Per-doctor style learned from their edits · snippets and macros (e.g. a "normal exam" block) · installable PWA with an offline queue · **expand the pilot to 20–30 doctors** |

**Exit KPIs:**
- WER: UZ ≤12%, RU ≤8%
- Drug-name and dosage recall ≥95%
- ≥30 weekly active doctors
- Self-reported time saved ≥1 h/day

---

## 4. Phase 3: clinic platform and integrations (Sprints 11–15)

| Sprint | Goal | Key stories |
|---|---|---|
| **S11** | **Organizations** | Clinic tenant and admin console · invites · roles (doctor, nurse, registrar, admin, auditor) · seat management · org-level templates and settings |
| **S12** | **Patient context** | Patient registry (PINFL optional) · visit history · **pre-visit summary** of earlier visits · upload labs and discharge papers (photo or PDF), OCR them and extract structured data · "ask the chart" |
| **S13** | **Interoperability** | **FHIR R5 export aligned with the DHP IG** (Patient, Encounter, Composition, Condition, Observation, MedicationRequest, ServiceRequest) · REST API and webhooks · **browser extension that fills any web EHR/MIS form** (a universal integration that needs no partner API) · first native integration with a design partner's MIS |
| **S14** | **DMED / DHP connection** | Apply for developer access early (week 8) · sandbox integration for encounter documents and e-prescription drafts · *external dependency: if access slips, the browser extension covers it* |
| **S15** | **Billing → v2.0 Clinic** | Subscriptions through Payme, Click and Uzum · plans and limits · clinic invoicing (bank transfer and e-invoice) · usage dashboard for clinic admins · sales collateral |

**Exit KPIs:**
- 2–3 paying clinics
- ≥100 weekly active doctors
- ≥1 live MIS integration

---

## 5. Phase 4: clinical copilot / CDSS (Sprints 16–21)

| Sprint | Goal | Key stories |
|---|---|---|
| **S16** | **Knowledge base** | Ingest the MoH national clinical protocols (UZ and RU), the drug register and WHO guidelines · retrieval that preserves citations · versioned knowledge · review UI for the clinical lead |
| **S17** | **Medication safety** | Drug–drug interactions (licensed or open source) · allergy cross-check · dose ranges, including pediatric weight-based and renal adjustment · **every alert shows its source** · accept/dismiss with a reason |
| **S18** | **Protocol adherence** | Diagnosis → relevant protocol → check for missing anamnesis, exam, tests or treatment · red flags · omissions shown on the note-review screen |
| **S19** | **Copilot Q&A** | Clinical questions in UZ or RU answered with citations from the knowledge base and literature · differential diagnosis as reference only |
| **S20** | **Institution protocols** | Clinics upload their own SOPs and formulary · rule configuration · per-clinic alert tuning to control alert fatigue |
| **S21** | **Clinical safety → v3.0 Copilot** | Hazard log and safety case · red-team test set · retrospective validation on pilot notes · **SaMD regulatory opinion. General availability is gated on this opinion** |

**Exit KPIs:**
- Alert precision ≥80%
- Zero critical safety incidents
- Protocol adherence measured against the baseline

---

## 6. Phase 5: audit and quality analytics (Sprints 22–25)

| Sprint | Goal | Key stories |
|---|---|---|
| **S22** | **Audit engine** | Check **100% of notes**: completeness against MoH form requirements, ICD-10 ↔ diagnosis ↔ treatment consistency, follow-up plan present. Runs on the Batch API at 50% cost |
| **S23** | **Quality dashboards** | Completeness and adherence trends by doctor and department · alerts accepted vs. dismissed · time-saved ROI for management |
| **S24** | **Auditor workspace** | Review queues, sampling rules, comments back to doctors, corrective-action tracking, exportable reports |
| **S25** | **Hardening → v4.0 Audit** | Load test (1,000 doctors) · penetration test · backup and disaster-recovery drill · performance work |

---

## 7. Phase 6: AI care team and expansion (Sprints 26–35, about 10 weeks)

| Sprints | Capability |
|---|---|
| 2 | **AI intake nurse**: a pre-visit questionnaire over Telegram (voice or text) that pre-fills the note |
| 2 | **Follow-up agent**: medication reminders, symptom check-ins, escalation to the doctor |
| 3 | **Inpatient**: ward rounds, shift handover and discharge-summary generation |
| 1–2 | **Clinic voice receptionist** for appointments, possibly built with a local voice-AI partner |
| ongoing | **New languages**: Karakalpak, Tajik, then Kazakh and Kyrgyz for regional expansion |

---

## 8. Parallel non-engineering track

| Week | Business, legal and clinical work |
|---|---|
| 1 | Recruit the clinical lead · engage legal counsel · write consent forms (UZ and RU) |
| 1–2 | **Record 30+ consented role-play consultations** (several specialties; UZ, RU and mixed) as the eval set |
| 2–4 | Sign 1–2 design-partner clinics, with a data-processing agreement |
| 4–6 | Legal opinion on data residency and whether voice counts as biometric data · privacy policy and terms of service in UZ and RU · personal-data database registration if required |
| 6 | **Pilot launch** |
| 8 | Apply for DMED developer access |
| 10–15 | First paying clinic · pricing validation |
| 14–20 | SaMD opinion for CDSS · clinical advisory board |

## 9. Top risks

| Risk | Mitigation |
|---|---|
| Uzbek ASR quality on code-switching and dialects | Bake-off in week 1 · our own consented data · fine-tuning · hotwords · the doctor always reviews |
| Hallucinated content in notes | Every statement links to its transcript evidence span · the model writes "not mentioned" instead of inventing · schema and rule validation · eval gate · the doctor signs |
| Regulation (residency, voice-as-biometric, SaMD) | Counsel engaged early · conservative architecture (audio and PII stay in UZ) · CDSS gated on the opinion |
| State DMED pilot competes with us | Private sector first · stay DMED/DHP-compatible · position as a partner or vendor |
| LLM cost vs. local price | Cost per note logged from Sprint 1 · caching · batch · self-hosted STT · an eval-backed model choice |
| Adoption and trust | Free tier · Telegram · clinic champions · visible sources · the doctor stays in control |
| Poor connectivity in the regions | Offline buffering · low-bitrate audio · resumable uploads |
| Dependency on DMED access | Browser-extension integration as a fallback |
