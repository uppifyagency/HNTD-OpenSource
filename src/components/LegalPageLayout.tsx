import Link from "next/link";
import { LEGAL_CONTACT_EMAIL } from "@/lib/legal";

interface Section {
  id: string;
  title: string;
}

interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  sections: Section[];
  children: React.ReactNode;
}

/**
 * Legal page shell — editorial skin (one reskin covers privacy / terms / gdpr). Editorial
 * header + bordered TOC + `.legal-prose` body (scoped typography in editorial.css). Server
 * component (no client hooks needed). Sits outside the dashboard layout, so it renders its
 * own .skin-editorial.
 */
export default function LegalPageLayout({ title, lastUpdated, sections, children }: LegalPageLayoutProps) {
  return (
    <div className="skin-editorial" style={{ minHeight: "100vh" }}>
      <main className="wrap" style={{ maxWidth: 840, padding: "32px var(--pad-x) 96px" }}>
        <Link href="/" className="mono dim" style={{ fontSize: 13, textDecoration: "none" }}>
          ← home
        </Link>

        <div className="issue-line" style={{ margin: "24px 0 16px" }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;legal</span>
          <span className="dim mono" style={{ fontSize: 12, marginLeft: "auto" }}>ultimo aggiornamento: {lastUpdated}</span>
        </div>

        <h1 className="mono" style={{ fontWeight: 700, fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 1, letterSpacing: "-0.02em", margin: "0 0 28px" }}>
          {title}
        </h1>

        {/* Table of Contents */}
        <nav style={{ border: "1px solid var(--rule-2)", padding: 18, marginBottom: 40 }}>
          <div className="kicker" style={{ marginBottom: 12 }}>contents</div>
          <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 6 }}>
            {sections.map((s, i) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="mono" style={{ fontSize: 13, color: "var(--ink)", textDecoration: "none" }}>
                  <span className="dim">{String(i + 1).padStart(2, "0")}</span>&nbsp;&nbsp;{s.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div className="legal-prose">{children}</div>

        <div style={{ marginTop: 48, paddingTop: 24, borderTop: "1px solid var(--rule-2)" }}>
          <p className="mono dim" style={{ fontSize: 13, margin: 0 }}>
            Domande su questa policy? Scrivici a{" "}
            <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} className="accent" style={{ textDecoration: "underline", textUnderlineOffset: 3 }}>
              {LEGAL_CONTACT_EMAIL}
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
