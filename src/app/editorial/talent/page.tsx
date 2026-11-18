"use client";

import { useState } from "react";
import { Nav, FileTab, StatusBar } from "@/components/editorial";
import { EditorialTalentPool } from "@/components/editorial/EditorialTalentPool";
import { talentPoolVM, type PoolDev } from "@/lib/talentPool/talentPoolViewModel";
import { samplePool } from "@/lib/talentPool/fixture";
import type { PoolCategory } from "@/lib/poolCategories";

/**
 * EDITORIAL TALENT POOL — Migrate preview (page 07: candidate index). No editorial mockup
 * existed for the pool; this previews the new design over a fixture. Renders the same
 * <EditorialTalentPool> the live /dashboard/talent-pool uses (which feeds talentPoolVM +
 * live FavoriteButton + POST /api/talent-pool/search). Here search filters the fixture
 * client-side (no API/auth locally); save buttons omitted. Client component for the state.
 * NB: no `export const metadata` — that's a server-only export; this preview route is
 * non-indexable by living under /editorial (covered by the swap-era robots posture).
 */
export default function EditorialTalentPreview() {
  const [activeCategory, setActiveCategory] = useState<PoolCategory | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PoolDev[] | null>(null);

  function runSearch() {
    const q = query.trim().toLowerCase();
    if (!q) { setResults(null); return; }
    setResults(
      samplePool.filter((d) =>
        [d.name, d.login, ...(d.topLanguages ?? [])].filter(Boolean).join(" ").toLowerCase().includes(q),
      ),
    );
  }

  const vm = talentPoolVM(samplePool, { activeCategory, searchResults: results });

  return (
    <div className="skin-editorial" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Nav
        links={[
          { label: "search", href: "/dashboard" },
          { label: "talent", href: "/dashboard/talent-pool", active: true },
          { label: "pipeline", href: "/dashboard/pipeline" },
          { label: "insights", href: "/dashboard/monitoring" },
        ]}
        tail={<FileTab id="07:talent.index" />}
        actions={[{ label: "[ settings ]", href: "/dashboard/settings", variant: "ghost" }]}
      />

      <main style={{ flex: 1, padding: "32px var(--pad-x) 96px" }}>
        <div className="issue-line" style={{ marginBottom: 24 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;talent pool</span>
          <span className="pagenum" style={{ marginLeft: "auto" }}>— vii —</span>
        </div>
        <EditorialTalentPool
          vm={vm}
          activeCategory={activeCategory}
          onCategorySelect={setActiveCategory}
          search={{
            query,
            onQueryChange: (q) => { setQuery(q); if (!q.trim()) setResults(null); },
            onSubmit: runSearch,
            onClear: () => { setQuery(""); setResults(null); },
            searching: false,
            error: null,
            resultCount: results === null ? null : results.length,
          }}
        />
      </main>

      <StatusBar
        left={[
          { label: <strong>TALENT</strong>, variant: "accent" },
          { label: `${vm.total} nel pool`, variant: "mute" },
        ]}
        right={[{ label: "preview · fixture data", variant: "mute" }]}
      />
    </div>
  );
}
