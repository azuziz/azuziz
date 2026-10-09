# Eval cases

Each folder in `cases/` is one consultation, used to compare speech-to-text providers and LLMs
([method](../docs/05-llm-comparison.md)).

```
cases/<id>/case.json     reference transcript, key facts, expected ICD-10 codes  (in git)
cases/<id>/audio.webm    the recording, if there is one: .webm .m4a .mp3 .wav .ogg .flac  (git-ignored)
```

## What's here now
Four **synthetic** cases written to exercise known risks. They still need review by the clinical lead (each has
`"review_status": "needs clinical review"`).

| Case | Conversation | Note language | Trap |
|---|---|---|---|
| 01-hypertension-uz-mixed | Uzbek + Russian terms | uz-Latn | dose increase **plus** a new drug |
| 02-pediatric-arvi-ru | Russian | ru | paracetamol dose corrected mid-sentence (5 ml → 10 ml) |
| 03-diabetes-uz-dose-correction | Uzbek | uz-Latn | penicillin allergy said once; metformin schedule corrected |
| 04-tonsillitis-mixed-allergy | switches every sentence | ru | amoxicillin allergy changes the antibiotic |

They have no audio yet, so they test the LLM step only. The Sprint 1 goal is 10 cases, and 30 by Sprint 4.

## Adding a case from a role-play recording
1. Get **written consent** from everyone speaking. Use role-plays only, never real patients, until the pilot's legal setup is done.
2. Create `cases/<nn>-<short-name>/` and put the recording in it as `audio.<ext>`.
3. Write `case.json` (copy an existing one):
   - `segments`: the **exact** words spoken, one entry per turn, with the speaker. This is the reference for WER.
   - `facts`: the clinically important facts. Mark drugs, doses and allergies `"critical": true`. `keywords` are
     cheap substring checks in the note's language: every group must match, and `a|b` means either.
   - `expected_icd10` / `acceptable_icd10`, `medical_terms` (scored for STT term recall), `output_language`, `specialty`.
4. Run `pytest -q` in `apps/api`. A test checks that every case loads and has a critical fact.

## case.json fields
| Field | Meaning |
|---|---|
| `conversation_language` | `uz`, `ru` or `uz+ru` (WER is reported per language) |
| `output_language` | `uz-Latn`, `uz-Cyrl` or `ru`: the note the model must write |
| `specialty` | `therapist`, `pediatrics`, `cardiology`, `obgyn`, `neurology`, `dentistry` |
| `synthetic` / `review_status` | provenance and clinical sign-off |
