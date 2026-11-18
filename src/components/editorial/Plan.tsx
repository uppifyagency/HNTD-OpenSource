import type { ReactNode } from "react";

/**
 * Pricing plan card. Styling in editorial.css (.plan*). Source: index.html / pricing.html.
 * Earned abstraction (Rule of Three): used by landing, pricing, settings.
 */
export type PlanProps = {
  name: string;
  /** small kicker eyebrow, e.g. "explore" / "scale" (mutually exclusive with pill) */
  eyebrow?: string;
  /** highlight pill, e.g. "recommended" (featured plan) */
  pill?: string;
  price: string; // e.g. "€390"
  suffix: string; // e.g. "/mese"
  /** optional lede paragraph under the price (pricing page); plain text on landing omits it */
  description?: ReactNode;
  features: ReactNode[];
  /** href for a link CTA, or onClick for a button CTA (e.g. opening a checkout). onClick wins. */
  cta: { label: string; href?: string; onClick?: () => void; disabled?: boolean; variant?: "ghost" | "primary" | "accent" };
  featured?: boolean;
};

export function Plan({ name, eyebrow, pill, price, suffix, description, features, cta, featured = false }: PlanProps) {
  const ctaClass = `btn${cta.variant ? ` btn--${cta.variant}` : ""}`;
  return (
    <div className={`plan${featured ? " plan--featured" : ""}`}>
      <div className="plan__head">
        <div className="plan__name">{name}</div>
        {pill ? <span className="plan__pill">{pill}</span> : eyebrow ? <span className="kicker">{eyebrow}</span> : null}
      </div>
      <div className="plan__price">
        <span className="plan__price-num">{price}</span>
        <span className="plan__price-suffix">{suffix}</span>
      </div>
      {description ? <p className="plan__lede sans">{description}</p> : null}
      <div className="plan__feat">
        <ul>
          {features.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>
      {cta.onClick ? (
        <button type="button" onClick={cta.onClick} disabled={cta.disabled} className={ctaClass}>
          {cta.label}
        </button>
      ) : (
        <a href={cta.href ?? "#"} className={ctaClass}>
          {cta.label}
        </a>
      )}
    </div>
  );
}
