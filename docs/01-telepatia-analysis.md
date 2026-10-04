# Telepatía AI: competitive teardown

> Research date: 2026-10-04. Our research environment blocked telepatia.ai directly, so this
> teardown draws on press coverage, investor announcements, app-store listings and their JMIR
> preprint. Traction numbers differ between sources because they were published at different
> dates, so read them as rough indicators.

## 1. Snapshot

| | |
|---|---|
| **What** | "AI Doctor": an ambient AI scribe plus a clinical copilot (CDSS) plus note auditing for doctors and hospitals |
| **Founded** | 2025. The founder was at Stanford; the company is Colombian (Medellín) |
| **Launch** | July 2025 in Colombia. HQ is now São Paulo |
| **CEO** | Nicolás Abad. He started the company after his father died at 58 from a preventable medical error |
| **Funding** | $9M seed (Oct 2025, led by A-Star; Canary, Abstract, Picus, SV Angel, Nido) and a $33M Series A (2026, led by a16z; Shyam Sankar of Palantir, David Vélez of Nubank and Simón Borrero of Rappi joined), for **$42M total** |
| **Markets** | Colombia, Brazil, Mexico, Chile, Argentina, plus individual doctors in Spain |
| **Next** | Rest of LatAm, then India, Africa and Southeast Asia |
| **Languages** | Spanish, Portuguese |

## 2. Reported traction

- 25+ health institutions, later reported as 40+, both public and private. Together these institutions employ **more than 100k doctors and nurses**.
- **12,000+ registered doctors**, **140k+ consultations per week**, 5M+ consultations processed and 14M patients reached.
- Colombia: in **9 of the 10 main hospitals**, including Fundación Santa Fe de Bogotá. Brazil: Hospital Mater Dei, where doctors keep it open about 8 h/day and **recover 1.7 h/day**.
- Outcome claims: institutional protocol adherence rose from **84% to 99%**, **60,000 medical errors** were prevented in real time, they say they catch "1 in 3 medical errors", and doctors save **about 2 h/day**.
- Goal: half of LatAm's 1.9M doctors by the end of 2027, and 20k Brazilian doctors by the end of 2026.

**Lesson:** it took them about 12 months from launch to 25+ institutions and a Series A. A focused,
doctor-first wedge can scale that fast.

## 3. Product modules

### 3.1 AI Scribe (ambient documentation): the wedge
- The doctor opens the app in the **browser on a phone or computer** and uses the microphone they already have. Nothing to install and no IT involvement. They also ship iOS and Android apps ("Telepatía: Asistente Médico AI").
- It listens to the doctor–patient conversation, **transcribes in real time** and drafts a **structured medical record**. Their slogan is "the note is ready when the patient leaves."
- Clinical content is mapped into **machine-readable fields**, not just free text. That structured data is what the later modules run on.
- The doctor reviews and edits the draft. During the visit they can keep eye contact with the patient instead of typing.

### 3.2 AI CDSS (clinical decision support)
- Real-time alerts for **drug interactions, doses and allergies, each shown with its source**.
- Live suggestions that follow medical literature and clinical guidelines, and flags for omissions.
- The knowledge is trained in **three layers**:
  1. peer-reviewed international literature (PubMed),
  2. **national clinical guidelines** for each country,
  3. **the institution's own protocols**.
- The doctor accepts or discards each suggestion, so the doctor stays in control.

### 3.3 Clinical note auditing
- **Every note is audited, instead of the usual manual sample of 1 in 30**: completeness, full ICD-10 coding, follow-up plans, protocol compliance and omissions.
- It supports institutional audit processes and organizes clinical and operational information.

### 3.4 Chart review ("second brain")
- Reviews existing medical records, finds information, organizes clinical data, **prioritizes exam results** and identifies patient-safety risks (as used at Mater Dei).

### 3.5 Enterprise platform
- Team-wide rollout, **institution-level note governance**, access controls and **EHR integration**.
- Clinical data is encrypted and **every access is logged and audited**.

### 3.6 Vision: an "AI workforce"
- AI doctors, AI nurses and AI auditors working across hospital systems.

## 4. Business model and go-to-market

| Motion | How |
|---|---|
| **Bottom-up (PLG)** | Free for independent doctors (core features), then an individual paid plan. Press reports about USD 99/month, with promos as low as USD 25/month; sources disagree |
| **Top-down (enterprise)** | Clinics, hospitals and networks, priced by team size, workflows and compliance needs. They land with the scribe and expand with CDSS and audit |
| **Evidence** | A JMIR Medical Informatics preprint (submitted May 2026) describes the integrated scribe and CDSS in Colombian and Brazilian primary care. Outcome numbers feature in all their marketing |
| **Brand** | The founder story, the "AI Doctor" positioning, and a mission statement about winning LatAm's first Nobel Prize in Medicine since 1984 |

## 5. Why it works: what we copy

1. **The scribe is the wedge.** It gives immediate, felt value (hours per day), needs no IT, and doctors pass it to each other.
2. **Free for individual doctors** drives distribution. Institutions are where the money comes from.
3. **Localization is the moat:** language, local note formats, national guidelines and each institution's protocols.
4. **Structured data, not just text.** The scribe is the data-capture layer that CDSS, audit and analytics are built on.
5. **Trust UX:** every alert cites its source, the doctor can accept or dismiss it, and nothing happens without the doctor.
6. **Sell outcomes with numbers** (adherence, errors prevented, time saved) to hospital management.

## 6. What we do differently for Uzbekistan

| Telepatía (LatAm) | Us (Uzbekistan) |
|---|---|
| Spanish, Portuguese | **Uzbek (Latin and Cyrillic) and Russian**, including **code-switching within a single consultation** |
| LatAm note formats | Post-Soviet / MoH Uzbekistan outpatient structure (Shikoyatlar / Жалобы, Anamnez, Ob'ektiv holat, Tashxis + ICD-10, ...) |
| WhatsApp is the dominant messenger | **Telegram-first**: a bot for voice notes and patient summaries |
| Local EHRs | **DMED** and the national **DHP (FHIR R5)**, plus local clinic MIS products. A browser extension can fill any web EHR |
| Card / USD billing | **Payme, Click, Uzum** for doctors; bank transfer and e-invoice for clinics |
| USD 25–99/month | Local price point, roughly USD 10–20/month for a doctor (to validate). This makes **cost per note a core engineering constraint** |
| National LatAm guidelines | **Uzbek MoH national clinical protocols** and the Uzbek state drug register (trade names mapped to INN/ATC) |

## Sources
- [The Next Web: Telepatia raises $33M led by a16z](https://thenextweb.com/news/telepatia-ai-healthcare-latin-america-33m-a16z)
- [a16z: Investing in Telepatia](https://a16z.com/announcement/investing-in-telepatia/)
- [LatamList: Series A](https://latamlist.com/telepatia-raises-33m-series-a-led-by-andreessen-horowitz/) · [LatamList: $9M seed](https://latamlist.com/telepatia-ai-raises-9m-seed-round/)
- [MobiHealthNews](https://www.mobihealthnews.com/news/telepatia-secures-33m-expand-ai-healthcare-platform-across-latin-america) · [HLTH](https://hlth.com/insights/news/telepatia-raises-33m-to-expand-ai-healthcare-platform-across-latin-america)
- [Bloomberg Law: AI health startup wants to assist half of LatAm doctors](https://news.bloomberglaw.com/health-law-and-business/ai-health-startup-wants-to-assist-half-of-latin-american-doctors)
- [Bloomberg Línea: "segundo cerebro" de los médicos](https://www.bloomberglinea.com/tecnologia/innovacion/la-startup-latinoamericana-que-quiere-convertir-la-ia-en-el-segundo-cerebro-de-los-medicos/)
- [Brazil Journal: AI Doctor / Mater Dei](https://braziljournal.com/startup-cria-ai-doctor-para-reduzir-mortes-evitaveis-e-quer-escalar-no-brasil/)
- [Valora Analitik](https://www.valoraanalitik.com/telepatia-ia-para-reducir-errores-medicos/) · [Pulse 2.0](https://pulse2.com/telepatia-raises-42-million-to-expand-ai-doctor-platform-across-latin-america/)
- [Telepatía website](https://www.telepatia.ai/en) · [Telepatía for doctors (ES)](https://www.telepatia.ai/es/medicos)
- [App Store listing](https://apps.apple.com/es/app/telepat%C3%ADa/id6741869566) · [Google Play listing](https://play.google.com/store/apps/details?id=com.telepatia.scribe)
- [JMIR preprint: Telepatia AI Scribe + CDSS](https://preprints.jmir.org/preprint/101788)
