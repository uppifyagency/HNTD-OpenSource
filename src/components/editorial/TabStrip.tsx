import type { ReactNode } from "react";

/**
 * Dossier-style tab strip. Styling in editorial.css (.tabs / .tabs__tab).
 * Source of truth: docs/hntd-redesign-v2/candidate.html.
 *
 * NOTE — in a server-component preview the tabs do NOT switch (no client state):
 * `activeKey` marks the visually-active tab and panels are rendered stacked below.
 * Client interactivity is wired at Migrate (would add "use client").
 */
export type Tab = { key: string; label: ReactNode };

export type TabStripProps = {
  tabs: Tab[];
  activeKey: string;
};

export function TabStrip({ tabs, activeKey }: TabStripProps) {
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button key={t.key} type="button" className={`tabs__tab${t.key === activeKey ? " is-active" : ""}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
