"use client";

import { useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserMenu, useSessionUser } from "@/lib/session";
import { isAdmin } from "@/lib/admin";

/**
 * EditorialShell — the authenticated dashboard chrome in the editorial skin.
 * Resolves migration nodes 1+3: a top nav with real links + <UserMenu>
 * (logout/account) + isAdmin-gated admin links + mobile bottom-tab, with the
 * scoped `.nav*` CSS from editorial.css (Connascence of Name).
 *
 * Dashboard pages render as children. EnsureUser stays a LAYOUT concern
 * (dashboard/layout.tsx) and wraps this shell.
 */
const BASE_LINKS = [
  { href: "/dashboard", label: "overview" },
  { href: "/dashboard/new-task", label: "match" },
  { href: "/dashboard/talent-pool", label: "talent" },
  { href: "/dashboard/pipeline", label: "pipeline" },
];
const ADMIN_LINKS = [
  { href: "/dashboard/monitoring", label: "insights" },
  { href: "/dashboard/admin", label: "admin" },
];
const SETTINGS_LINK = { href: "/dashboard/settings", label: "settings" };

export function EditorialShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const admin = isAdmin(useSessionUser()?.email);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  const isActive = (href: string) =>
    href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href);

  const deskLinks = [...BASE_LINKS, ...(admin ? ADMIN_LINKS : []), SETTINGS_LINK];
  const overflowLinks = [...(admin ? ADMIN_LINKS : []), SETTINGS_LINK];

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (moreRef.current && !moreRef.current.contains(e.target as Node)) setMoreOpen(false);
  }, []);
  useEffect(() => {
    if (!moreOpen) return;
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [moreOpen, handleClickOutside]);
  useEffect(() => setMoreOpen(false), [pathname]);

  const isOverflowActive = overflowLinks.some((l) => isActive(l.href));

  return (
    <div className="skin-editorial ed-shell">
      {/* ── Top nav (desktop links hidden <768 via .nav__links) ── */}
      <header className="nav">
        <div className="wrap nav__inner">
          <Link href="/dashboard" className="nav__brand">
            <span className="nav__brand-mark" /> HNTD<span className="dim">/</span>
            <span className="dim">intel</span>
          </Link>
          <nav className="nav__links">
            {deskLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`nav__link${isActive(l.href) ? " is-active" : ""}`}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <div className="nav__spacer" />
          <div className="nav__userbtn">
            <UserMenu />
          </div>
        </div>
      </header>

      {/* bare content slot — each page owns its .wrap (per-page max-width) + padding */}
      <main className="ed-shell__main">{children}</main>

      {/* ── Mobile bottom-tab: 4 core + more (admin/settings) ── */}
      <div className="ed-mobtab" ref={moreRef}>
        {moreOpen && (
          <div className="ed-mobtab__more">
            {overflowLinks.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`ed-mobtab__moreitem${isActive(l.href) ? " is-active" : ""}`}
              >
                {l.label}
              </Link>
            ))}
          </div>
        )}
        <nav className="ed-mobtab__bar">
          {BASE_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`ed-mobtab__tab${isActive(l.href) ? " is-active" : ""}`}
            >
              {l.label}
            </Link>
          ))}
          <button
            type="button"
            onClick={() => setMoreOpen((p) => !p)}
            className={`ed-mobtab__tab${isOverflowActive || moreOpen ? " is-active" : ""}`}
          >
            more
          </button>
        </nav>
      </div>
    </div>
  );
}
