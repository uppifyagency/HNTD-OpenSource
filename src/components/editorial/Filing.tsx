import type { CSSProperties, ReactNode } from "react";

/**
 * Filing-cabinet card — the editorial signature container.
 * Styling lives in editorial.css (.filing*). This is a thin structural
 * wrapper with named props. Source of truth: docs/hntd-redesign-v2 candidate.html.
 */
export type FilingProps = {
  /** cabinet-tab label, top-left (e.g. "dossier · classified open-source") */
  tab?: string;
  /** render the tab in ghost (outline) style */
  ghostTab?: boolean;
  /** corner mark, top-right (e.g. "⊕ 07.candidate.json") */
  corner?: string;
  /** subtle hover lift + border darken */
  hover?: boolean;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
};

export function Filing({
  tab,
  ghostTab = false,
  corner,
  hover = false,
  className = "",
  style,
  children,
}: FilingProps) {
  return (
    <section className={`filing${hover ? " filing--hover" : ""}${className ? ` ${className}` : ""}`} style={style}>
      {tab ? (
        <span className={`filing__tab${ghostTab ? " filing__tab--ghost" : ""}`}>{tab}</span>
      ) : null}
      {corner ? <span className="filing__corner">{corner}</span> : null}
      {children}
    </section>
  );
}
