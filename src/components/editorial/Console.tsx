/**
 * Inline mono "console" prompt input (.console). The search/query box on app views.
 * Thin structural wrapper, named props; styling lives in editorial.css (.console*).
 * Source of truth: docs/hntd-redesign-v2/dashboard.html. Reused by match (JD input).
 *
 * Server-preview: the input is uncontrolled (defaultValue, no onChange) — the live
 * wiring plugs in at MIGRATE. `action` renders a trailing button inside the box.
 */
export type ConsoleAction = { label: string; variant?: "primary" | "accent" | "ghost" };

export type ConsoleProps = {
  value: string;
  placeholder?: string;
  prompt?: string;
  caret?: boolean;
  hint?: string;
  action?: ConsoleAction;
};

export function Console({ value, placeholder, prompt = ">", caret = false, hint, action }: ConsoleProps) {
  return (
    <div className="console">
      <span className="console__prompt">{prompt}</span>
      <input className="console__input" defaultValue={value} placeholder={placeholder ?? value} />
      {caret ? <span className="caret" /> : null}
      {hint ? <span className="console__hint">{hint}</span> : null}
      {action ? (
        <button type="button" className={`btn btn--${action.variant ?? "primary"} btn--sm`} style={{ marginLeft: 8 }}>
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
