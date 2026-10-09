import type { Segment } from "@/lib/types";

export function TranscriptView({ segments, highlighted }: { segments: Segment[]; highlighted: number[] }) {
  return (
    <ol className="transcript">
      {segments.map((s) => (
        <li
          key={s.id}
          id={`segment-${s.id}`}
          className={highlighted.includes(s.id) ? "is-highlighted" : undefined}
        >
          <span className="segment-id">{s.id}</span>
          <div>
            {s.speaker && <span className="segment-speaker">{s.speaker}</span>}
            <p>{s.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
