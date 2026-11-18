import type { ReactNode } from "react";

/**
 * vim/tmux-style sticky footer present on every product page.
 * Styling lives in editorial.css (.statusbar*). Source of truth: candidate.html.
 */
export type StatusSeg = {
  label: ReactNode;
  variant?: "accent" | "mute" | "default";
};

export type StatusBarProps = {
  left?: StatusSeg[];
  right?: StatusSeg[];
};

function segClass(variant: StatusSeg["variant"]): string {
  if (variant === "accent") return "statusbar__seg statusbar__seg--accent";
  if (variant === "mute") return "statusbar__seg statusbar__seg--mute";
  return "statusbar__seg";
}

export function StatusBar({ left = [], right = [] }: StatusBarProps) {
  return (
    <div className="statusbar">
      {left.map((s, i) => (
        <span key={`l-${i}`} className={segClass(s.variant)}>
          {s.label}
        </span>
      ))}
      <span className="statusbar__spacer" />
      {right.map((s, i) => (
        <span
          key={`r-${i}`}
          className={`${segClass(s.variant)}${i === right.length - 1 ? " statusbar__seg--right" : ""}`}
        >
          {s.label}
        </span>
      ))}
    </div>
  );
}
