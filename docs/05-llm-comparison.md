# LLM comparison: Kimi vs MiMo-V2.6-Pro vs GPT Luna

> Prices checked on 2026-10-06 from public listings. Confirm each one on the provider's own console before quoting it
> to anyone. Prices change often and most of these models are only weeks old.

## 1. Candidates

| | **GPT-6 Luna** | **MiMo-V2.6-Pro** | **Kimi K2.6** | **Kimi K3** |
|---|---|---|---|---|
| Vendor | OpenAI (US) | Xiaomi (China) | Moonshot AI (China) | Moonshot AI (China) |
| Model ID | `gpt-6-luna` | `mimo-v2.6-pro` | `kimi-k2.6` | `kimi-k3` |
| Released | 2026-09-22 | 2026-09-21 | 2026-04 | 2026-07 (open weights) |
| $/MTok input | 0.10 | 0.43 | 0.95 | 3.00 |
| $/MTok cached input | 0.01 | 0.0036 | 0.16 | 0.30 |
| $/MTok output | 0.50 | 0.87 | 4.00 | 15.00 |
| Context | 1.05M | 1M | 262K | 1.05M |
| Structured output | **Native JSON schema** | JSON mode only (no `json_schema`). We validate and retry | JSON schema | to verify |
| Open weights | No | **Yes, MIT** (1T total / 42B active; FP8 checkpoint; smaller Flash and 9B distill) | Yes (1T / 32B active) | Yes, custom "Kimi K3 License" (2.8T / 104B active) |
| Extras | Zero data retention on request; EU data residency | Accepts **audio** input directly (worth testing audio → note) | Tool calling, caching | Premium tier |
| API style | OpenAI | OpenAI-compatible | OpenAI-compatible | OpenAI-compatible |

All four can be called through **one OpenAI-compatible adapter**: only the base URL, model ID and key change.

We test both Kimi tiers because K2.6 and K3 differ about 3.5× in price. We test GPT-6 Luna rather than GPT-5.6 Luna
because the newer one is cheaper ($0.10/$0.50 vs $0.20/$1.20).

## 2. Cost per consultation

Assumptions for one 15-min consultation: 6–10k uncached transcript tokens, a 4k cached system prompt and template, and
2.5–5k output tokens (note plus reasoning). Each model has its own tokenizer and Uzbek tokenizes very differently
across them, so **the bake-off measures the real token counts**. These numbers are only a starting estimate.

| Model | $ per consult | $ per doctor-month (300 consults) | $ per 1,000 notes |
|---|---|---|---|
| GPT-6 Luna | 0.002–0.004 | **0.6–1.1** | 1.9–3.5 |
| MiMo-V2.6-Pro | 0.005–0.009 | **1.4–2.6** | 4.8–8.7 |
| Kimi K2.6 | 0.016–0.030 | **4.9–9.0** | 16–30 |
| Kimi K3 | 0.057–0.106 | **17–32** | 57–106 |

**What this means:**
- With Luna or MiMo, **LLM cost is no longer the constraint.** It is under 10% of a USD 10–20/month price. **Speech
  recognition becomes the main variable cost**, which is why self-hosted STT in Phase 2 matters.
- Kimi K3 costs about the same as the premium models in the earlier estimate, so it is only worth it if it is clearly
  better on Uzbek. It could still be useful as a fallback for hard cases.
- At these prices we can **run two models on every note** (one drafts, the other checks drugs and doses against the
  transcript) and still spend less than one premium model. We test this in Sprint 7.

## 3. Data-transfer rules (must be solved before real patient data, not before the bake-off)

Uzbekistan's list of 49 approved countries (Cabinet resolution of 2026-07-29) decides where personal data can go
without extra approval:
- **The US counts only for companies in the EU–US Data Privacy Framework.** Check that OpenAI is certified. OpenAI
  also offers **EU data residency**, and EU countries are on the list.
- **China does not appear on the published list.** Sending patient data, even de-identified, to Moonshot's or Xiaomi's
  own APIs in China would need another legal basis (approved standard contractual clauses or similar). Ask counsel.

How to use Kimi or MiMo legally in production if one of them wins:
1. **A host in an approved country.** These open-weights models are served by many inference providers and clouds
   (for example MiMo through Alibaba Cloud Model Studio, plus US/EU inference providers). We pin a provider whose
   servers are in an approved jurisdiction.
2. **Self-host in Uzbekistan.** The licenses allow it (MiMo is MIT). But a 1T-parameter model needs about 8 high-end
   GPUs (≈1 TB of FP8 weights), which is far too expensive at our stage. MiMo's smaller Flash or 9B variants are a
   realistic self-host option *if* their quality is good enough. We test them later.

**The bake-off itself only uses role-plays and synthetic transcripts (no real patients)**, so we can call all
providers directly for it.

## 4. Test method

**Test set.** We grow it from 10 cases in Sprint 1 to 30 by Sprint 4:
- The same **reference transcript** goes to every model, so we compare the LLMs and not the speech recognition.
- Conversation languages: Uzbek, Russian and mixed. Output languages: `uz-Latn`, `uz-Cyrl` and `ru`.
- Six specialties. Cases include traps: a drug name said in Russian inside Uzbek speech, a dose correction mid-conversation
  ("5 mg... no, 10 mg"), an allergy mentioned once in passing, and things the doctor never said.
- The clinical lead writes a **gold note** and a **list of key facts** for each case.

**Metrics:**

| Metric | How measured | Weight |
|---|---|---|
| **Hallucination** (statements not supported by the transcript) | LLM judge against the transcript, 20% checked by a human. **Any invented or wrong drug, dose or allergy is a critical error** | Gate + 25% |
| **Clinical recall** (key facts captured) | Gold fact list vs note, LLM judge plus human spot-check | 35% |
| **Language quality** (Uzbek grammar and terms, correct script with oʻ/gʻ and no Cyrillic leaking into Latin output, natural Russian) | Script checker (automatic) plus a blind doctor rating from 1 to 5 | 20% |
| **ICD-10 accuracy** | Exact or acceptable match with the gold code | 5% |
| **Schema validity** | % of first responses that are valid JSON for our note schema | Gate (≥98% after one retry) |
| **Latency** | p50 and p95, from transcript in to note out | 5% |
| **Cost** | Real token counts × price | 10% |

**Judge:** a strong model that is **not one of the candidates**, plus human spot-checks, so no model grades itself.

**Decision rule:**
1. Drop any model with a **critical drug, dose or allergy error** on the test set, or schema validity under 98%.
2. Rank the rest by weighted score.
3. The clinical lead does a **blind side-by-side review** of the top 2 on 10 cases. If they clearly prefer one, that one wins.
4. Record the result in `docs/adr/0002-llm-provider.md`. Keep the runner-up configured as an automatic **fallback**
   for outages.

**When to run it:**
- **Sprint 1:** quick run on 10 cases → pick the default model for the pilot.
- **Sprint 4:** full run on 30 cases with blind doctor review → confirm the choice.
- **Sprint 7:** re-run on de-identified real pilot data, and test two-model cross-checking.
- **After that:** monthly and whenever a candidate releases a new version. These models change every few weeks, and
  the adapter makes switching a config change.

## Sources
- [OpenAI docs: GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna.md) · [Technology.org: GPT-6 Sol and Luna pricing](https://www.technology.org/2026/09/23/openai-gpt-6-sol-luna-pricing-benchmarks/) · [GPT-5.6 Luna vs GPT-6 Luna](https://www.callmissed.com/blog/gpt-luna-api-pricing-context-window-benchmarks)
- [OpenRouter: MiMo-V2.6-Pro](https://openrouter.ai/xiaomi/mimo-v2.6-pro) · [pricepertoken: MiMo v2.6 Pro](https://pricepertoken.com/pricing-page/model/xiaomi-mimo-v2.6-pro) · [Requesty: MiMo-V2.6-Pro](https://www.requesty.ai/models/xiaomi/mimo-v2.6-pro) · [eesel: MiMo V2.6 open model](https://www.eesel.ai/blog/xiaomi-mimo-v2-6) · [Times of AI: MiMo open weights](https://www.timesofai.com/news/xiaomi-mimo-v2-6-pro-open-weights/) · [Alibaba Cloud Model Studio: MiMo](https://help.aliyun.com/en/model-studio/mimo)
- [BenchLM: Kimi API pricing](https://benchlm.ai/moonshot/api-pricing) · [OpenRouter: Kimi K2.6](https://openrouter.ai/moonshotai/kimi-k2.6) · [OpenRouter: Kimi K3](https://openrouter.ai/moonshotai/kimi-k3) · [OpenRouter: Is Kimi K3 open source?](https://openrouter.ai/blog/insights/kimi-k3-open-source/) · [Puter: Kimi API pricing](https://developer.puter.com/tutorials/kimi-api-pricing/)
- [Kun.uz: 49 approved countries](https://kun.uz/en/news/2026/08/04/uzbekistan-approves-49-countries-for-simplified-personal-data-transfers) · [Prae Legal: list of countries with equivalent protection](https://praelegal.uz/news-and-publications/uzbekistan-approves-list-of-countries-with-an-equivalent-level-of-personal-data-protection)
