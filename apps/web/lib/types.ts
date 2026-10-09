export type OutputLanguage = "uz-Latn" | "uz-Cyrl" | "ru";

export interface LlmOption {
  id: string;
  label: string;
  available: boolean;
}

export interface AppConfig {
  default_llm: string;
  llms: LlmOption[];
  stt_provider: { id: string; label: string };
  output_languages: OutputLanguage[];
  specialties: string[];
  demo_mode: boolean;
  max_upload_mb: number;
}

export interface Segment {
  id: number;
  speaker: string | null;
  start: number | null;
  end: number | null;
  text: string;
}

export interface NoteSection {
  key: string;
  heading: string;
  body: string;
  evidence: number[];
}

export interface NoteRun {
  model: string;
  output_language: OutputLanguage;
  created_at: string;
  sections?: NoteSection[];
  text?: string;
  metrics?: {
    model: string;
    input_tokens: number;
    cached_input_tokens: number;
    output_tokens: number;
    llm_latency_s: number;
    llm_cost_usd: number;
    attempts: number;
  };
  warnings?: string[];
  error?: string;
}

export type EncounterStatus = "uploaded" | "transcribing" | "generating" | "done" | "failed";

export interface Encounter {
  id: string;
  status: EncounterStatus;
  error: string | null;
  output_language: OutputLanguage;
  specialty: string;
  transcript: { segments: Segment[]; language: string | null; duration_s: number | null } | null;
  stt_metrics: { provider: string; stt_latency_s: number; stt_cost_usd: number | null } | null;
  note_runs: NoteRun[];
}
