import type { ReactNode } from "react";

/**
 * ASCII commit heatmap (the "ASCII-viz" widget family).
 * Styling in editorial.css (.commit-heatmap). Source of truth: candidate.html.
 * `grid` is the verbatim multi-line block (month header + 7 day rows); it is
 * rendered white-space:pre with overflow-x:auto so the wide grid scrolls inside
 * its box rather than overflowing the viewport on mobile.
 */
export type CommitHeatmapProps = {
  grid: string;
  scale: string; // legend glyph ramp, e.g. "░ ▁ ▂ ▃ ▄ ▅ ▆ ▇ █"
  annotation: ReactNode; // peak / gap note
};

export function CommitHeatmap({ grid, scale, annotation }: CommitHeatmapProps) {
  return (
    <>
      <div className="commit-heatmap">{grid}</div>
      <div className="commit-heatmap__legend">
        <span>less</span>
        <span style={{ letterSpacing: "1px" }}>{scale}</span>
        <span>more</span>
        <span style={{ marginLeft: "auto" }}>{annotation}</span>
      </div>
    </>
  );
}
