import type { CSSProperties, ReactNode } from "react";

/**
 * Print-style table wrapper (.ptable). Thin structural wrapper — sections supply
 * <thead>/<tbody> with .row-num/.num cells. Styling in editorial.css. Source: index.html.
 * `borderless` drops the outer rule (the KPI variant uses border:0).
 */
export type PrintTableProps = {
  borderless?: boolean;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
};

export function PrintTable({ borderless = false, className = "", style, children }: PrintTableProps) {
  const merged: CSSProperties = borderless ? { border: 0, ...style } : (style ?? {});
  // overflow-x wrapper: on narrow screens a wide table scrolls instead of
  // overflowing the viewport (the mobile min-width comes from .ptable--cmp).
  return (
    <div style={{ overflowX: "auto", maxWidth: "100%" }}>
      <table className={`ptable${className ? ` ${className}` : ""}`} style={merged}>
        {children}
      </table>
    </div>
  );
}
