"use client";

import { useEffect, useState } from "react";
import { NoteView } from "@/components/NoteView";
import { Recorder } from "@/components/Recorder";
import { TranscriptView } from "@/components/TranscriptView";
import { getConfig, getEncounter, regenerateNote, uploadEncounter } from "@/lib/api";
import { LANGUAGE_LABELS, SPECIALTY_LABELS, STATUS_STEPS } from "@/lib/labels";
import type { AppConfig, Encounter, OutputLanguage } from "@/lib/types";

const IN_PROGRESS = new Set(["uploaded", "transcribing", "generating"]);

export default function Home() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [language, setLanguage] = useState<OutputLanguage>("uz-Latn");
  const [specialty, setSpecialty] = useState("therapist");
  const [llmModel, setLlmModel] = useState("");
  const [uploading, setUploading] = useState(false);
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [activeRun, setActiveRun] = useState(0);
  const [highlighted, setHighlighted] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConfig()
      .then((c) => {
        setConfig(c);
        setLlmModel(c.default_llm);
      })
      .catch((e: Error) => setConfigError(e.message));
  }, []);

  // Poll while the encounter is being processed.
  const encounterId = encounter?.id;
  const inProgress = encounter ? IN_PROGRESS.has(encounter.status) : false;
  useEffect(() => {
    if (!encounterId || !inProgress) return;
    const t = setInterval(async () => {
      try {
        const next = await getEncounter(encounterId);
        setEncounter(next);
        if (!IN_PROGRESS.has(next.status)) setActiveRun(Math.max(next.note_runs.length - 1, 0));
      } catch (e) {
        setError((e as Error).message);
      }
    }, 1200);
    return () => clearInterval(t);
  }, [encounterId, inProgress]);

  async function handleAudio(blob: Blob, filename: string) {
    setError(null);
    setUploading(true);
    try {
      const { id } = await uploadEncounter({ audio: blob, filename, outputLanguage: language, specialty, llmModel });
      setEncounter(await getEncounter(id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function handleRegenerate(model: string, lang: OutputLanguage) {
    if (!encounter) return;
    setError(null);
    try {
      await regenerateNote(encounter.id, model, lang);
      setEncounter({ ...encounter, status: "generating" });
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function showEvidence(ids: number[]) {
    setHighlighted(ids);
    document.getElementById(`segment-${ids[0]}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function reset() {
    setEncounter(null);
    setActiveRun(0);
    setHighlighted([]);
    setError(null);
    setConsent(false);
  }

  const step = uploading ? "uploading" : encounter?.status === "uploaded" ? "transcribing" : encounter?.status;
  const stepIndex = STATUS_STEPS.findIndex((s) => s.key === step);
  const hasNote = (encounter?.note_runs.length ?? 0) > 0;

  return (
    <main className="page">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>azuziz scribe</span>
        </div>
        {encounter && (
          <button type="button" onClick={reset}>
            New consultation
          </button>
        )}
      </header>

      {config?.demo_mode && (
        <div className="banner" role="status">
          Demo mode: fake speech recognition and/or a fake model are active, so notes are placeholders. Add API keys to
          use real providers.
        </div>
      )}
      {configError && (
        <p className="error" role="alert">
          Can&apos;t reach the API ({configError}). Is it running?
        </p>
      )}

      {!encounter && (
        <section className="card setup" aria-label="New consultation">
          <h1>New consultation</h1>
          <div className="field">
            <span className="field-label">Note language</span>
            <div className="segmented" role="radiogroup" aria-label="Note language">
              {(config?.output_languages ?? (["uz-Latn", "uz-Cyrl", "ru"] as OutputLanguage[])).map((l) => (
                <button
                  key={l}
                  type="button"
                  role="radio"
                  aria-checked={language === l}
                  className={language === l ? "is-active" : undefined}
                  onClick={() => setLanguage(l)}
                >
                  {LANGUAGE_LABELS[l]}
                </button>
              ))}
            </div>
          </div>
          <div className="field-row">
            <label className="field">
              <span className="field-label">Specialty</span>
              <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
                {(config?.specialties ?? ["therapist"]).map((s) => (
                  <option key={s} value={s}>
                    {SPECIALTY_LABELS[s] ?? s}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field-label">AI model</span>
              <select value={llmModel} onChange={(e) => setLlmModel(e.target.value)}>
                {config?.llms.map((m) => (
                  <option key={m.id} value={m.id} disabled={!m.available}>
                    {m.label}
                    {m.available ? "" : " (no API key)"}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="consent">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>The patient agreed to this consultation being recorded.</span>
          </label>
          <Recorder
            disabled={!consent || !config || uploading}
            disabledReason={!consent ? "Confirm the patient's consent first." : undefined}
            onAudio={handleAudio}
          />
        </section>
      )}

      {(uploading || encounter) && (
        <ol className="steps" aria-label="Progress">
          {STATUS_STEPS.map((s, i) => (
            <li
              key={s.key}
              className={
                encounter?.status === "failed" && i === Math.max(stepIndex, 0)
                  ? "is-failed"
                  : i < stepIndex || step === "done"
                    ? "is-done"
                    : i === stepIndex
                      ? "is-active"
                      : undefined
              }
            >
              {s.label}
            </li>
          ))}
        </ol>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {encounter?.status === "failed" && !hasNote && (
        <p className="error" role="alert">
          {encounter.error}
        </p>
      )}

      {encounter && (hasNote || encounter.transcript) && (
        <div className="result">
          {hasNote && config && (
            <NoteView
              key={encounter.note_runs.length}
              runs={encounter.note_runs}
              activeIndex={Math.min(activeRun, encounter.note_runs.length - 1)}
              onSelect={setActiveRun}
              onEvidence={showEvidence}
              llms={config.llms}
              busy={encounter.status === "generating"}
              onRegenerate={handleRegenerate}
            />
          )}
          {encounter.transcript && (
            <section className="card" aria-label="Transcript">
              <div className="card-header">
                <h2>Transcript</h2>
                {encounter.stt_metrics && (
                  <span className="muted">
                    {encounter.stt_metrics.provider} · {encounter.stt_metrics.stt_latency_s.toFixed(1)} s
                  </span>
                )}
              </div>
              <TranscriptView segments={encounter.transcript.segments} highlighted={highlighted} />
            </section>
          )}
        </div>
      )}
    </main>
  );
}
