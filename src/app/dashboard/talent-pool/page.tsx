"use client";

import { useState } from "react";
import { useQuery } from "convex/react";
import { useSession } from "@/lib/session";
import { api } from "../../../../convex/_generated/api";
import type { PoolCategory } from "@/lib/poolCategories";
import { FavoriteButton } from "@/components/FavoriteButton";
import { SkeletonCardGroup } from "@/components/SkeletonCard";
import { EditorialTalentPool } from "@/components/editorial/EditorialTalentPool";
import { talentPoolVM, type PoolDev } from "@/lib/talentPool/talentPoolViewModel";

/**
 * Live talent pool (Step 5 Migrate). Same reads (developers.listPool, plan-gated blur server-side)
 * and same semantic-search IO (POST /api/talent-pool/search with a Clerk "convex" token) as the V4
 * page, but the body is the editorial <EditorialTalentPool vm={talentPoolVM(...)}>. The pure adapter
 * owns category counts + filter + card mapping; this page owns state, fetch and the FavoriteButton.
 * Renders under .skin-editorial inside the V4 dashboard layout for now (top-nav flips to EditorialShell
 * at cutover; preview at /editorial/talent). Live data confirms on app.hntd.it post-deploy.
 * NOTE: per-field useVisibility flags (talentPool.*) not threaded — node-2 follow-on.
 */
export default function TalentPoolPage() {
  const pool = useQuery(api.developers.listPool) as PoolDev[] | undefined;
  const session = useSession();
  const [activeCategory, setActiveCategory] = useState<PoolCategory | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PoolDev[] | null>(null);
  const [snippets, setSnippets] = useState<Record<string, string>>({});
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  async function handleSearch() {
    if (!searchQuery.trim()) {
      clearSearch();
      return;
    }
    setSearching(true);
    setSearchError(null);
    try {
      const token = session.status === "signedIn" ? await session.getToken() : null;
      const res = await fetch("/api/talent-pool/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, token }),
      });
      // UI-05: a failed request must surface as an error, never as "0 results"
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setSearchResults(null);
        setSnippets({});
        setSearchError(body?.error ?? "Ricerca fallita. Riprova.");
        return;
      }
      const data = await res.json();
      setSearchResults(data.results ?? []);
      setSnippets(data.snippets ?? {});
    } catch (err) {
      console.error("Search failed:", err);
      setSearchResults(null);
      setSnippets({});
      setSearchError("Ricerca fallita. Controlla la connessione e riprova.");
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setSearchQuery("");
    setSearchResults(null);
    setSnippets({});
    setSearchError(null);
  }

  const vm = talentPoolVM(pool ?? [], { activeCategory, searchResults, snippets });

  return (
    <div className="skin-editorial">
      <div className="wrap" style={{ padding: "24px var(--pad-x) 64px", maxWidth: "100%" }}>
        <div className="issue-line" style={{ marginBottom: 16 }}>
          <span className="issue-line__label">HNTD&nbsp;·&nbsp;talent pool</span>
          <span className="dim mono" style={{ fontSize: 12 }}>
            {pool === undefined ? "…" : `${pool.length} sviluppatori pre-analizzati`}
          </span>
        </div>

        {pool === undefined ? (
          <SkeletonCardGroup count={4} />
        ) : (
          <EditorialTalentPool
            vm={vm}
            activeCategory={activeCategory}
            onCategorySelect={setActiveCategory}
            search={{
              query: searchQuery,
              onQueryChange: (q) => {
                setSearchQuery(q);
                if (!q.trim()) clearSearch();
              },
              onSubmit: handleSearch,
              onClear: clearSearch,
              searching,
              error: searchError,
              resultCount: searchResults === null ? null : searchResults.length,
            }}
            renderSave={(card) => <FavoriteButton developerId={card.id} size="lg" />}
          />
        )}
      </div>
    </div>
  );
}
