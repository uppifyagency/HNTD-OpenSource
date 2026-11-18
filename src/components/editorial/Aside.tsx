import type { ReactNode } from "react";

/**
 * Editorial aside panel. Two named variants — the mockup reused one `.aside`
 * class for both, a Connascence-of-Name collision we split here (see editorial.css):
 *   - "sidecar" (default): the ~40% rail beside a form/main column in a `.split`
 *     (signup). Default keeps existing callers unchanged.
 *   - "rail": the dashboard left filter sidebar inside an `.app` grid.
 * Thin structural wrapper with named props; styling lives in editorial.css.
 * Source of truth: docs/hntd-redesign-v2/{signup,dashboard}.html.
 */
export type AsideProps = {
  variant?: "sidecar" | "rail";
  className?: string;
  children: ReactNode;
};

export function Aside({ variant = "sidecar", className = "", children }: AsideProps) {
  return <aside className={`aside aside--${variant}${className ? ` ${className}` : ""}`}>{children}</aside>;
}
