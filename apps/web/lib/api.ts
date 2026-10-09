import type { AppConfig, Encounter, OutputLanguage } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_URL}${path}`, init);
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // keep the status text
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export function getConfig(): Promise<AppConfig> {
  return request("/api/config");
}

export function uploadEncounter(args: {
  audio: Blob;
  filename: string;
  outputLanguage: OutputLanguage;
  specialty: string;
  llmModel: string;
}): Promise<{ id: string; status: string }> {
  const form = new FormData();
  form.append("audio", args.audio, args.filename);
  form.append("consent", "true");
  form.append("output_language", args.outputLanguage);
  form.append("specialty", args.specialty);
  form.append("llm_model", args.llmModel);
  return request("/api/encounters", { method: "POST", body: form });
}

export function getEncounter(id: string): Promise<Encounter> {
  return request(`/api/encounters/${id}`);
}

export function regenerateNote(id: string, llmModel: string, outputLanguage: OutputLanguage) {
  return request<{ id: string; status: string }>(`/api/encounters/${id}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ llm_model: llmModel, output_language: outputLanguage }),
  });
}
