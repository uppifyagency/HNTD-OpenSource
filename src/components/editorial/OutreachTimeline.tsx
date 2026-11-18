import type { ReactNode } from "react";

/**
 * Syslog-format outreach contact log + action bar.
 * Styling in editorial.css (.outreach-log + .ts/.em/.ok helper spans).
 * Source of truth: candidate.html. The syslog body is passed as children
 * (a <pre> preserves the whitespace/indentation); colored spans use tokens,
 * never hex (the mockup's bespoke hex is mapped to the mono-tonal palette).
 */
export type OutreachAction = { label: string; variant?: "accent" | "ghost" };

export type OutreachTimelineProps = {
  children: ReactNode; // syslog body (pre content with .ts/.em/.ok spans)
  actions: OutreachAction[];
};

export function OutreachTimeline({ children, actions }: OutreachTimelineProps) {
  return (
    <>
      <pre className="outreach-log">{children}</pre>
      <div className="outreach-log__actions">
        {actions.map((a, i) => (
          <button key={i} type="button" className={`btn btn--${a.variant ?? "ghost"} btn--sm`}>
            {a.label}
          </button>
        ))}
      </div>
    </>
  );
}
