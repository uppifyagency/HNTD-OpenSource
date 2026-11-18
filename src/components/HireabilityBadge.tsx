import { hireabilitySignal } from "@/lib/hireability";

/**
 * Surfaces the developer's SELF-DECLARED GitHub "Available for hire" flag, contextualised
 * by their current company (the company × hireable quadrant). Renders nothing for the
 * undeclared quadrants — we never claim a dev is "not hireable".
 *
 * Spec: artifacts/hireability-badge/SPEC.md · logic: src/lib/hireability.ts
 */
export function HireabilityBadge({
  hireable,
  company,
}: {
  hireable?: boolean | null;
  company?: string | null;
}) {
  const signal = hireabilitySignal(hireable, company);
  if (!signal.show) return null;

  return (
    <span
      className="inline-flex items-center gap-2 border border-border rounded-lg px-3 py-1.5 font-mono text-xs font-semibold text-ok"
      title="Self-declared 'Available for hire' on GitHub"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-ok" />
      {signal.label}
      <span className="font-normal text-muted-foreground">&middot; {signal.context}</span>
    </span>
  );
}
