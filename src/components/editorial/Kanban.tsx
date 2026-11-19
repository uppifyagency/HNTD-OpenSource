import type { CSSProperties, ReactNode } from "react";

/**
 * Kanban board family for the hiring pipeline. Thin structural wrappers; styling
 * lives in editorial.css (.kanban / .kcol / .kcard). Source of truth: pipeline.html.
 *
 * Tone variants (border/background) are mapped here so pages stay declarative and
 * the mockup's inline `var(--accent)` — which would resolve transparent under this
 * skin (it's the shadcn HSL triplet) — is routed through `var(--ed-accent)`.
 */
export type KanbanProps = { children: ReactNode };

export function Kanban({ children }: KanbanProps) {
  return <section className="kanban">{children}</section>;
}

export type KColumnProps = {
  title: ReactNode;
  count: ReactNode;
  /** the "hire" column: accent header + inverted count */
  accent?: boolean;
  children: ReactNode;
};

export function KColumn({ title, count, accent = false, children }: KColumnProps) {
  return (
    <div className="kcol">
      <div className="kcol__head" style={accent ? { background: "var(--ed-accent)", color: "var(--paper)" } : undefined}>
        <span>{title}</span>
        <span className="kcol__count" style={accent ? { background: "var(--paper)", color: "var(--ed-accent)" } : undefined}>
          {count}
        </span>
      </div>
      <div className="kcol__body">{children}</div>
    </div>
  );
}

export type KCardTone = "default" | "active" | "interview" | "hire" | "pass";

const TONE_STYLE: Record<KCardTone, CSSProperties | undefined> = {
  default: undefined,
  active: { borderColor: "var(--ink)" },
  interview: { background: "var(--paper-2)", borderColor: "var(--ink)" },
  hire: { background: "var(--paper)", borderColor: "var(--ed-accent)", borderWidth: 2 },
  pass: { opacity: 0.55 },
};

export type KCardProps = {
  href?: string;
  id: ReactNode;
  name: string;
  stack: ReactNode;
  score: ReactNode;
  tone?: KCardTone;
  /** optional extra line below the meta row (e.g. interview stage, offer terms) */
  extra?: ReactNode;
};

export function KCard({ href = "#", id, name, stack, score, tone = "default", extra }: KCardProps) {
  return (
    <div className="kcard" style={TONE_STYLE[tone]}>
      <div className="kcard__id">{id}</div>
      <a href={href} className="kcard__name">
        {name}
      </a>
      <div className="kcard__meta">
        <span>{stack}</span>
        <span>·</span>
        <span className="kcard__score">{score}</span>
      </div>
      {extra}
    </div>
  );
}
