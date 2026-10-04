# Uzbekistan: market, language, technology and regulation

> Research date: 2026-10-04. The regulatory notes are an engineering summary, **not legal advice**.
> Getting a formal opinion from local counsel is a Sprint 1–6 task (see the roadmap).

## 1. Market

| Fact | Value | So what |
|---|---|---|
| Doctors | 29 per 10,000 people, which with ~37.5M people works out to **≈105–110k doctors** (our derived estimate; verify against MoH statistics) | The total addressable market for doctor seats |
| Private clinics | Grew from ~3,000–3,500 (2017) to **9,000+ (2025)**; private providers deliver 30–35% of services | **Our beachhead.** Private clinics can decide fast and pay for productivity |
| State digitization | **DMED** is the unified digital-health operator: 97% of institutions connected, 53 information systems integrated, **free connection for private clinics**, APIs for developers | Integration target and a channel |
| National interoperability | **Digital Health Platform (DHP)**: built by Uzinfocom with the MoH, funded by KfW, runs 2024–2027, uses **HL7 FHIR R5**, ICD-11, SNOMED CT, LOINC, ATC, UCUM, with OAuth2/RBAC/consent/audit. The implementation guide is still a work in progress | **Model our data FHIR-first from day 1** |
| e-Prescription | Rolling out in stages: Tashkent city plus 15 pilot districts | Output target from Phase 3 on |
| **Government AI pilot** | The 2026 AI roadmap (60+ projects) includes a **digital medical assistant with speech recognition, integrated into DMED**, piloting in Tashkent's Almazar and Yunusabad districts, the Republican Oncology Center and **one private clinic** | The state is building something similar for public polyclinics. We should (1) win the private sector first, (2) stay DMED/DHP-compatible so we can become a vendor or partner, and (3) beat it on quality, specialty depth and UX |

## 2. How language works in an Uzbek consultation

- **Uzbek** is the official language, and **Latin** script is official. **Cyrillic** is still widely used, especially by older doctors and in existing documents.
- **Russian** is widespread in medicine (education, terminology, documentation, especially in Tashkent). Drug names are usually said in Russian or Latin.
- **Code-switching is the norm.** Doctors use Uzbek sentences with Russian medical terms. Patients speak regional dialects (Fergana, Khorezm, Surkhandarya...). Karakalpak is spoken in Karakalpakstan, and Tajik in parts of Samarkand and Bukhara.
- **Product implications:**
  - The ASR must handle UZ and RU mixed within a single utterance.
  - **The note's output language is chosen separately from the conversation language:** `uz-Latn`, `uz-Cyrl` or `ru`.
  - The patient summary is written in *the patient's* language, in plain words.
  - Notes follow the post-Soviet outpatient structure, not US SOAP:

    | Uzbek (Latin) | Russian | Meaning |
    |---|---|---|
    | Shikoyatlar | Жалобы | Complaints |
    | Kasallik anamnezi | Анамнез заболевания | History of present illness |
    | Hayot anamnezi | Анамнез жизни | Past and social history, allergies, heredity |
    | Ob'ektiv holat (+ lokal holat) | Объективный статус (+ локальный статус) | Physical exam |
    | Tashxis (ICD-10) | Диагноз (МКБ-10) | Diagnosis |
    | Tekshiruv rejasi | План обследования | Work-up plan |
    | Davolash / tayinlovlar | Лечение / назначения | Treatment |
    | Tavsiyalar, nazorat | Рекомендации, явка | Recommendations, follow-up |

  - Clinics still use **ICD-10** in practice, while DHP specifies ICD-11, so we support both, mapping between them.

## 3. Speech and AI technology landscape

| Component | Options | Notes |
|---|---|---|
| Hosted Uzbek STT | **ElevenLabs Scribe**: 15.9% WER on FLEURS Uzbek (its vendor page compares this with 96.7% for un-fine-tuned Whisper large-v3) | Fastest way to start. Sends audio abroad, so a legal review is needed |
| Open-weights STT | **GigaAM-Multilingual** (Sber, July 2026; 220M/600M Conformer; described as best-in-class open source for **RU, UZ, KK, KY**). Fine-tuned Whisper-medium for Uzbek reaches ~16.7% WER | **Self-host in Uzbekistan** from Phase 2. That covers data residency and removes the per-minute cost |
| Local speech companies | Aisha AI, UzbekVoice.ai, Lynx AI | Possible STT vendors, partners or benchmarks |
| Datasets | Uzbek Speech Corpus (USC, 105 h, 958 speakers), Common Voice, FLEURS | **There is no public UZ↔RU medical code-switching dataset.** Our consented clinical data becomes a moat |
| Russian-language medical voice | Voice2Med and Sber's voice-filled records (Russia) | These are **dictation** tools for Russian, not ambient Uzbek conversation. That is the gap we fill |
| LLM | Claude via the Anthropic API: structured outputs (JSON schema), prompt caching, `inference_geo` | Measure Uzbek quality with our own eval set |
| Compute in UZ | **UzCloud** (Uztelecom national cloud: IaaS, S3, backup); new Tier III data centers with **GPU servers** (Bukhara and Kokand, Sep 2026); DataVolt TAS-1 AI data center in Tashkent IT Park (first capacity Nov 2026); local GPU rental, e.g. an A40 48GB listed at ≈23.4M UZS/month | Host audio, PII and self-hosted ASR inside Uzbekistan |

## 4. Regulation (engineering summary, not legal advice)

### 4.1 Personal data: Law No. 1125, amending the Law "On Personal Data", in force 2026-03-27
- **Mandatory in-country storage** now applies only to **biometric data, genetic data and telecom users' data**.
- Other personal data may be stored or processed abroad if (a) the country is recognized as **adequate** (49 countries approved in 2026, including the US, Germany, the UK and others), (b) standard contractual clauses or binding corporate rules approved by the authority are used, or (c) approved international standards are followed.
- Health data is a **special category**, so the highest-care handling applies.
- **Open question for counsel:** is a consultation *voice recording* "biometric data"? It is usually treated as biometric only when processed to identify a person, which we don't do. We still design conservatively:
  - **Audio and identifiable PII are stored and processed in Uzbekistan**, or audio isn't stored at all once transcription is done.
  - **Only de-identified transcript text** is sent to a foreign LLM API.
  - We record patient consent for every encounter.
  - We also check whether our personal-data databases must be registered with the authorized body, and whether we must appoint a responsible person.

### 4.2 AI law, in force 2026-01-21, and the AI ethics rules (Order No. 3787, in force 2026-06-17)
- AI-generated content must be labeled. The law bans AI uses that harm health or rights, and sets administrative liability for unlawful processing of personal data with AI (fines of 50–100 BCU).
- **Our design:** every note is shown as an "AI draft" until a doctor signs it, the signed note records "verified by Dr X", a human stays in the loop, and an audit trail is kept.

### 4.3 Medical devices
- Medical devices need **MoH state registration**: 6–12 months by the national route, or about 15 days through recognition of an FDA/CE/MHRA/PMDA/MFDS approval.
- **AI Scribe** (documentation that the doctor verifies) is probably *not* a medical device. **CDSS** (dose and interaction alerts, diagnostic suggestions) **may be software as a medical device (SaMD)**.
- So we get a **regulatory opinion before CDSS reaches general availability** (Phase 4). CDSS is positioned as *reference information with sources, where the physician decides*.

### 4.4 Still to research
- Health insurance and reimbursement rules, as they affect the value of coding and audit (Phase 5).
- Legal status of e-signatures on clinical notes, and DMED's rules for third-party submissions.

## 5. Unit economics (the hard constraint)

Local willingness to pay is roughly **USD 10–20 per doctor per month** (a hypothesis we validate in the pilot). An
active private-clinic doctor sees about **15 patients/day, ≈300 consultations/month**.

**LLM cost per 15-minute consultation.** Assumptions: the transcript is about 6–10k input tokens (Uzbek tokenizes less
efficiently than English), the system prompt, template and glossary add about 4k tokens and are cached, and the
note plus reasoning is about 3–4k output tokens. Prices are list prices as of 2026-09.

| Model | $/MTok in / out | ≈ $ per consult | ≈ $ per doctor-month (300 consults) |
|---|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`, default) | 4 / 20 | 0.10–0.15 | 30–45 |
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | 2 / 10 | 0.05–0.07 | 15–21 |
| Claude Haiku 4.5 (`claude-haiku-4-5`) | 1 / 5 | 0.02–0.03 | 6–9 |

STT cost comes on top. Hosted APIs charge per audio-minute, so we verify current prices in Sprint 1. A self-hosted
GPU is a fixed ≈USD 1.8–1.9k/month, so it pays off once there are enough active doctors.

**Conclusions:**
1. **We log cost per note from Sprint 1**, alongside latency and quality.
2. We start on Opus 5.5, the highest quality, which matters most while we learn. **Moving note drafting to a cheaper
   model is a business decision** that we make only after our eval shows quality is equal (Sprint 7).
3. Levers that don't cost quality: prompt caching; the **Batch API (50% off)** for non-real-time jobs such as 100% note
   auditing; self-hosted STT; trimming silence and small talk before the LLM.
4. Pricing: limit the free tier by notes per month, and give clinic plans per-seat pricing with fair use.

## Sources
- [DMED: Uzbekistan's unified digital healthcare operator](https://dmed.uz/en)
- [Uzbekistan Digital Health Platform: FHIR R5 implementation guide](https://build.fhir.org/ig/uzinfocom-org/digital-health-ig/en/index.html)
- [MoH: e-prescription implemented in stages (yuz.uz)](https://yuz.uz/en/news/minzdrav-elektronny-retsept-budet-vnedryatsya-poetapno)
- [Gazeta.uz: Government approves AI projects list](https://www.gazeta.uz/en/2025/08/09/ai-in-project/) · [Kun.uz: AI in healthcare, courts, public services](https://kun.uz/en/news/2025/07/22/uzbekistan-to-integrate-ai-into-healthcare-courts-and-public-services)
- [Euronews: Uzbekistan overhauls healthcare (2026)](https://www.euronews.com/business/2026/02/17/uzbekistan-overhauls-healthcare-with-digital-systems-and-modern-facilities) · [gov.uz: healthcare sector review](https://gov.uz/en/news/view/52561)
- [Dentons: Uzbekistan dismantles strict data localization regime](https://www.dentons.com/en/insights/articles/2026/march/31/uzbekistan-dismantles-strict-data-localization-regime)
- [Kun.uz: personal data law amended](https://kun.uz/en/news/2026/03/27/uzbekistan-amends-personal-data-law-to-facilitate-global-payment-systems) · [Kun.uz: 49 adequate countries](https://kun.uz/en/news/2026/08/04/uzbekistan-approves-49-countries-for-simplified-personal-data-transfers)
- [Legal500: AI and personal data legislative updates](https://www.legal500.com/developments/thought-leadership/legislative-updates-in-the-field-of-artificial-intelligence-and-personal-data-regulation-uzbekistan/) · [Dunyo: AI law in force](https://dunyo.info/en/news/v-uzbekistane-vstupil-v-silu-zakon-reguliruyushchiy-ispolzovanie)
- [MSP: state registration of medical devices in Uzbekistan](https://mspcorporate.com/state-registration-of-medical-devices-uzbekistan.html)
- [ElevenLabs: Uzbek speech-to-text](https://elevenlabs.io/speech-to-text/uzbek)
- [GigaAM-Multilingual (Hugging Face)](https://huggingface.co/ai-sage/GigaAM-Multilingual) · [paper](https://arxiv.org/pdf/2607.10371)
- [Kotib/uzbek_stt_v1 (Whisper-medium fine-tune)](https://huggingface.co/Kotib/uzbek_stt_v1) · [USC: Uzbek Speech Corpus](https://arxiv.org/pdf/2107.14419)
- [Aisha AI](https://aisha.group/en) · [UzbekVoice.ai](https://uzbekvoice.ai/en-US) · [Lynx AI](https://lynx-ai.uz/en/solutions/speech-to-text)
- [gov.uz: Uztelecom data centers in Bukhara and Kokand](https://gov.uz/en/digital/news/view/222857) · [DataVolt TAS-1](https://aiweekly.co/alerts/datavolt-and-nvidia-kick-off-central-asias-ai-data-center-race) · [Local GPU listing](https://www.whtop.com/plans/pro-data.tech/147041)
