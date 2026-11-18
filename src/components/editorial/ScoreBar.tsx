import type { CSSProperties, ReactNode } from "react";

/**
 * ASCII-styled score bar with optional "why" caption.
 * Styling lives in editorial.css (.score*). Source of truth: candidate.html.
 * `pct` is 0..1 (scaleX of the fill). `value`/`max` are the textual readout.
 */
export type ScoreBarProps = {
  label: string;
  value: number | string;
  max?: number | string;
  /** fill fraction 0..1 */
  pct: number;
  accent?: boolean;
  caption?: ReactNode;
};

export function ScoreBar({ label, value, max, pct, accent = false, caption }: ScoreBarProps) {
  const barStyle = { "--score": pct } as CSSProperties;
  return (
    <div>
      <div className="score">
        <span className="score__label">{label}</span>
        <span className="score__value mono">
          <strong>{value}</strong>
          {max != null ? <> / {max}</> : null}
        </span>
        <div className={`score__bar${accent ? " score__bar--accent" : ""}`} style={barStyle}>
          <div className="score__bar-fill" />
        </div>
      </div>
      {caption ? (
        <p className="sans dim" style={{ fontSize: 13, margin: "8px 0 0", lineHeight: 1.55 }}>
          {caption}
        </p>
      ) : null}
    </div>
  );
}
