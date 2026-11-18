"use client";

import { useMemo } from "react";

/* Deterministic pseudo-random based on cell index — avoids hydration mismatch */
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/* Generate a contribution level (0–4) with realistic distribution */
function contributionLevel(index: number): number {
  const r = seededRandom(index + 42);
  if (r < 0.55) return 0; // empty
  if (r < 0.72) return 1; // light
  if (r < 0.85) return 2; // medium
  if (r < 0.94) return 3; // high
  return 4; // very high
}

const LEVEL_COLORS = [
  "hsl(120 5% 91%)",           // 0 — empty
  "hsl(142 40% 78%)",          // 1 — lightest green
  "hsl(142 50% 58%)",          // 2 — light green
  "hsl(142 64% 40%)",          // 3 — medium green
  "hsl(142 64% 28%)",          // 4 — dark green
];

const WEEKS = 52;
const DAYS = 7;
const CELL_SIZE = 11;
const GAP = 3;

export function GitHubGrid({ position }: { position: "top" | "bottom" }) {
  const cells = useMemo(() => {
    if (position === "bottom") return [];
    return Array.from({ length: WEEKS * DAYS }, (_, i) => ({
      id: i,
      level: contributionLevel(i),
    }));
  }, [position]);

  if (position === "bottom") return null;

  const gridWidth = WEEKS * (CELL_SIZE + GAP) - GAP;
  const gridHeight = DAYS * (CELL_SIZE + GAP) - GAP;

  return (
    <div
      className="absolute inset-x-0 top-0 pointer-events-none overflow-hidden contrib-grid-mask"
      style={{ height: gridHeight + 80 }}
      aria-hidden="true"
    >
      <div
        className="mx-auto"
        style={{
          width: gridWidth,
          maxWidth: "100%",
          paddingTop: 32,
          display: "grid",
          gridTemplateColumns: `repeat(${WEEKS}, ${CELL_SIZE}px)`,
          gridTemplateRows: `repeat(${DAYS}, ${CELL_SIZE}px)`,
          gap: `${GAP}px`,
          opacity: 0.35,
        }}
      >
        {cells.map((cell) => (
          <div
            key={cell.id}
            className="contrib-cell"
            style={{
              backgroundColor: LEVEL_COLORS[cell.level],
              width: CELL_SIZE,
              height: CELL_SIZE,
            }}
          />
        ))}
      </div>
    </div>
  );
}
