"use client";

import { useState } from "react";
import { LANGUAGE_LABELS } from "@/lib/labels";
import type { LlmOption, NoteRun, OutputLanguage } from "@/lib/types";

export function NoteView({
  runs,
  activeIndex,
  onSelect,
  onEvidence,
  llms,
  busy,
  onRegenerate,
}: {
  runs: NoteRun[];
  activeIndex: number;
  onSelect: (i: number) => void;
  onEvidence: (ids: number[]) => void;
  llms: LlmOption[];
  busy: boolean;
  onRegenerate: (model: string, language: OutputLanguage) => void;
}) {
  const run = runs[activeIndex];
  const [copied, setCopied] = useState(false);
  const [model, setModel] = useState(() => {
    const available = llms.filter((m) => m.available);
    return (available.find((m) => m.id !== run?.model) ?? available[0])?.id ?? "";
  });
  const [language, setLanguage] = useState<OutputLanguage>(run?.output_language ?? "uz-Latn");
  const labelOf = (id: string) => llms.find((m) => m.id === id)?.label ?? id;

  async function copy() {
    if (!run?.text) return;
    await navigator.clipboard.writeText(run.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="card note-card" aria-label="Draft note">
      <div className="card-header">
        <h2>Draft note</h2>
        <span className="badge">AI draft · review before signing</span>
      </div>

      {runs.length > 1 && (
        <div className="tabs" role="tablist" aria-label="Note versions">
          {runs.map((r, i) => (
            <button
              key={`${r.model}-${r.created_at}`}
              type="button"
              role="tab"
              aria-selected={i === activeIndex}
              className={i === activeIndex ? "tab is-active" : "tab"}
              onClick={() => onSelect(i)}
            >
              {labelOf(r.model)} · {LANGUAGE_LABELS[r.output_language]}
            </button>
          ))}
        </div>
      )}

      {run?.error ? (
        <p className="error" role="alert">
          {run.error}
        </p>
      ) : run?.sections?.length ? (
        <>
          <div className="note-sections">
            {run.sections.map((s) => (
              <div key={s.key} className="note-section">
                <h3>{s.heading}</h3>
                <p>{s.body}</p>
                {s.evidence.length > 0 && (
                  <button type="button" className="evidence" onClick={() => onEvidence(s.evidence)}>
                    source: {s.evidence.map((i) => `#${i}`).join(" ")}
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="note-actions">
            <button type="button" className="primary" onClick={copy}>
              {copied ? "Copied" : "Copy note"}
            </button>
          </div>
          {run.metrics && (
            <p className="metrics">
              {labelOf(run.model)} · {run.metrics.llm_latency_s.toFixed(1)} s · $
              {run.metrics.llm_cost_usd.toFixed(4)} · {run.metrics.input_tokens.toLocaleString()} in /{" "}
              {run.metrics.output_tokens.toLocaleString()} out tokens
              {run.metrics.attempts > 1 ? ` · ${run.metrics.attempts} attempts` : ""}
            </p>
          )}
          {run.warnings?.map((w) => (
            <p key={w} className="warning">
              {w}
            </p>
          ))}
        </>
      ) : (
        <p className="muted">Nothing was recorded in this note.</p>
      )}

      <div className="regenerate">
        <span className="muted">Compare with another model:</span>
        <select value={model} onChange={(e) => setModel(e.target.value)} aria-label="Model">
          {llms.map((m) => (
            <option key={m.id} value={m.id} disabled={!m.available}>
              {m.label}
              {m.available ? "" : " (no API key)"}
            </option>
          ))}
        </select>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as OutputLanguage)}
          aria-label="Note language"
        >
          {(Object.keys(LANGUAGE_LABELS) as OutputLanguage[]).map((l) => (
            <option key={l} value={l}>
              {LANGUAGE_LABELS[l]}
            </option>
          ))}
        </select>
        <button type="button" disabled={busy || !model} onClick={() => onRegenerate(model, language)}>
          {busy ? "Writing…" : "Generate"}
        </button>
      </div>
    </section>
  );
}
