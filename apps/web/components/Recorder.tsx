"use client";

import { useRef } from "react";
import { useRecorder } from "@/lib/useRecorder";

function formatTime(s: number): string {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function Recorder({
  disabled,
  disabledReason,
  onAudio,
}: {
  disabled: boolean;
  disabledReason?: string;
  onAudio: (blob: Blob, filename: string) => void;
}) {
  const { state, elapsed, error, start, stop } = useRecorder();
  const fileInput = useRef<HTMLInputElement>(null);
  const recording = state === "recording";

  async function toggle() {
    if (recording) {
      const result = await stop();
      if (result) onAudio(result.blob, result.filename);
    } else {
      await start();
    }
  }

  return (
    <div className="recorder">
      <button
        type="button"
        className={`record-button${recording ? " is-recording" : ""}`}
        onClick={toggle}
        disabled={(disabled && !recording) || state === "requesting"}
        aria-label={recording ? "Stop recording" : "Start recording"}
      >
        <span className="record-icon" aria-hidden="true" />
      </button>
      <div className="record-meta">
        <div className="record-time" aria-live="polite">
          {recording ? (
            <>
              <span className="live-dot" aria-hidden="true" /> {formatTime(elapsed)}
            </>
          ) : state === "requesting" ? (
            "Allow microphone…"
          ) : (
            "Tap to record"
          )}
        </div>
        <div className="record-hint">
          {recording
            ? "Tap again when the consultation ends."
            : disabled
              ? disabledReason
              : "Speak normally — Uzbek, Russian or both."}
        </div>
        {!recording && (
          <button
            type="button"
            className="link-button"
            disabled={disabled}
            onClick={() => fileInput.current?.click()}
          >
            or upload a recording
          </button>
        )}
        <input
          ref={fileInput}
          type="file"
          accept="audio/*,video/webm,video/mp4"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onAudio(file, file.name);
            e.target.value = "";
          }}
        />
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
