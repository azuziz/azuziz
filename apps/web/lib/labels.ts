import type { OutputLanguage } from "./types";

// UI text is English for Sprint 1; Uzbek and Russian UI arrive in Sprint 2. Note content is already localized.
export const LANGUAGE_LABELS: Record<OutputLanguage, string> = {
  "uz-Latn": "Oʻzbekcha",
  "uz-Cyrl": "Ўзбекча",
  ru: "Русский",
};

export const SPECIALTY_LABELS: Record<string, string> = {
  therapist: "Therapist / GP",
  pediatrics: "Pediatrics",
  cardiology: "Cardiology",
  obgyn: "OB/GYN",
  neurology: "Neurology",
  dentistry: "Dentistry",
};

export const STATUS_STEPS = [
  { key: "uploading", label: "Uploading" },
  { key: "transcribing", label: "Transcribing" },
  { key: "generating", label: "Writing note" },
  { key: "done", label: "Ready" },
] as const;
