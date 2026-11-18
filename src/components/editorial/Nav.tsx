import type { ReactNode } from "react";

/**
 * Editorial top nav (chrome). Styling in editorial.css (.nav*). Source: index.html.
 */
export type NavLink = { label: ReactNode; href: string; active?: boolean };
export type NavAction = { label: ReactNode; href: string; variant?: "ghost" | "primary" | "accent" };

function btnClass(variant: NavAction["variant"]): string {
  const v = variant ? ` btn--${variant}` : "";
  return `btn${v} btn--sm`;
}

export type NavProps = {
  brand?: ReactNode;
  /** where the brand mark links; default "/". Auth pages on app.hntd.it must point to the
   *  apex (https://hntd.it) because "/" there redirects to /dashboard → /sign-in (a loop). */
  brandHref?: string;
  links: NavLink[];
  actions: NavAction[];
  /** optional slot before the actions (e.g. a <FileTab> on app views like the dossier) */
  tail?: ReactNode;
};

export function Nav({ brand, brandHref = "/", links, actions, tail }: NavProps) {
  return (
    <header className="nav">
      <div className="wrap nav__inner">
        <a href={brandHref} className="nav__brand">
          {brand ?? (
            <>
              <span className="nav__brand-mark" /> HNTD<span className="dim">/</span>
              <span className="dim">intel</span>
            </>
          )}
        </a>
        <nav className="nav__links">
          {links.map((l, i) => (
            <a key={i} href={l.href} className={`nav__link${l.active ? " is-active" : ""}`}>
              {l.label}
            </a>
          ))}
        </nav>
        <div className="nav__spacer" />
        {tail ? <div className="nav__tail">{tail}</div> : null}
        <div className="nav__actions">
          {actions.map((a, i) => (
            <a key={i} href={a.href} className={btnClass(a.variant)}>
              {a.label}
            </a>
          ))}
        </div>
      </div>
    </header>
  );
}
