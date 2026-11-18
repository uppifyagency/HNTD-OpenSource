import { Fragment } from "react";

/**
 * Horizontal step indicator for multi-step flows (onboarding). Thin structural
 * wrapper; styling lives in editorial.css (.stepper*). Source of truth: onboarding.html.
 * The number is the 1-based position; separators are auto-inserted between steps.
 */
export type StepStatus = "done" | "active" | "todo";
export type Step = { label: string; status?: StepStatus };
export type StepperProps = { steps: Step[] };

function stepClass(status: StepStatus | undefined): string {
  if (status === "done") return "stepper__step is-done";
  if (status === "active") return "stepper__step is-active";
  return "stepper__step";
}

export function Stepper({ steps }: StepperProps) {
  return (
    <div className="stepper">
      {steps.map((s, i) => (
        <Fragment key={i}>
          {i > 0 ? <span className="stepper__sep" /> : null}
          <div className={stepClass(s.status)}>
            <span className="stepper__num">{i + 1}</span>
            <span>{s.label}</span>
          </div>
        </Fragment>
      ))}
    </div>
  );
}
