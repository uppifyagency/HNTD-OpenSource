"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import SmartTagInput, { type TagItem } from "@/components/SmartTagInput";
import { useVisibility } from "@/hooks/useVisibility";
import { convexErrorMessage } from "@/lib/convexError";

/**
 * New-search form — editorial skin (Migrate, "match" body). Reskinned in place: same logic,
 * state, validation, createTask mutation and useVisibility gating as the V4 form; only the
 * controls are editorial (native <select> over shadcn, sharp 1px borders, mono). Rollback =
 * git revert. The fake JD "engine output log" from the match.html mockup is intentionally
 * absent — there is no streaming backend. Renders under .skin-editorial (live page + preview).
 */

const COUNTRY_OPTIONS = [
  { value: "italy", label: "Italy" },
  { value: "germany", label: "Germany" },
  { value: "france", label: "France" },
  { value: "spain", label: "Spain" },
  { value: "uk", label: "United Kingdom" },
  { value: "netherlands", label: "Netherlands" },
  { value: "portugal", label: "Portugal" },
  { value: "poland", label: "Poland" },
  { value: "switzerland", label: "Switzerland" },
];

const controlStyle = {
  width: "100%",
  border: "1px solid var(--rule-2)",
  background: "var(--paper)",
  color: "var(--ink)",
  padding: "11px 14px",
  fontFamily: "var(--mono, monospace)",
  fontSize: 14,
  outline: "none",
} as const;

function Kicker({ children }: { children: React.ReactNode }) {
  return <div className="kicker" style={{ marginBottom: 8 }}>{children}</div>;
}

export default function NewTaskForm() {
  const router = useRouter();
  const currentUser = useQuery(api.users.getCurrentUser);
  const createTask = useMutation(api.tasks.createTask);

  const showManualMode = useVisibility("newTask.manualMode");
  const showSearchTerms = useVisibility("newTask.manualMode.searchTerms");
  const showCountry = useVisibility("newTask.manualMode.country");
  const showCity = useVisibility("newTask.manualMode.city");
  const showMinActivity = useVisibility("newTask.manualMode.minActivity");
  const showJdMode = useVisibility("newTask.jdMode");
  const showJobDescription = useVisibility("newTask.jdMode.jobDescription");
  const showMaxResults = useVisibility("newTask.maxResults");

  const [activeTab, setActiveTab] = useState<"manual" | "jd">("jd");

  // Manual mode fields
  const [searchTags, setSearchTags] = useState<TagItem[]>([]);
  const [country, setCountry] = useState("");
  const [city, setCity] = useState("");
  const [minActivity, setMinActivity] = useState(6);

  // JD mode field
  const [jobDescription, setJobDescription] = useState("");

  // Shared
  const [maxResults, setMaxResults] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;

    setLoading(true);
    setError(null);
    try {
      if (activeTab === "manual") {
        // Split tags into languages (green) and keywords (blue)
        const languages = searchTags
          .filter((t) => t.isLanguage)
          .flatMap((t) => t.entry?.searchLanguages ?? [t.term]);
        const keywords = searchTags
          .filter((t) => !t.isLanguage)
          .flatMap((t) => t.entry?.searchKeywords ?? [t.term]);
        // For "both" strategy terms, also include their searchLanguages
        const extraLanguages = searchTags
          .filter((t) => !t.isLanguage && t.entry?.strategy === "both")
          .flatMap((t) => t.entry?.searchLanguages ?? []);
        const allLanguages = [...new Set([...languages, ...extraLanguages])];

        await createTask({
          mode: "manual",
          params: {
            languages: allLanguages.length > 0 ? allLanguages : languages,
            locations: city ? [city.trim().toLowerCase(), country] : [country],
            country,
            city: city.trim() || undefined,
            minActivity,
            keywords: keywords.length > 0 ? keywords : undefined,
            maxResults,
          },
        });
      } else {
        await createTask({
          mode: "jd",
          jobDescription,
          params: { languages: [], locations: [], minActivity: 6, maxResults },
        });
      }
      router.push("/dashboard");
    } catch (err) {
      // A production Convex deployment redacts `err.message` to "Server Error"; only an
      // application error's `data` survives, so read that FIRST.
      setError(convexErrorMessage(err) ?? "Impossibile creare la ricerca. Riprova.");
    } finally {
      setLoading(false);
    }
  };

  const isManualValid = searchTags.length > 0 && country !== "";
  const isJdValid = jobDescription.trim().length >= 50;
  const isValid = activeTab === "manual" ? isManualValid : isJdValid;

  const modeCard = (active: boolean) =>
    ({
      border: active ? "2px solid var(--ink)" : "1px solid var(--rule-2)",
      padding: active ? "19px" : "20px", // keep box size stable across the border swap
      cursor: "pointer",
      background: "var(--paper)",
    }) as const;

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Mode cards */}
      {(showManualMode || showJdMode) && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          {showJdMode && (
            <div onClick={() => { setActiveTab("jd"); setMaxResults((p) => Math.min(p, 50)); }} style={modeCard(activeTab === "jd")}>
              <div className="mono" style={{ fontSize: 18, marginBottom: 8 }}>&gt;_</div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Da Job Description</div>
              <div className="mono dim" style={{ fontSize: 12 }}>Incolla una JD per il match AI</div>
            </div>
          )}
          {showManualMode && (
            <div onClick={() => { setActiveTab("manual"); setMaxResults((p) => Math.min(p, 20)); }} style={modeCard(activeTab === "manual")}>
              <div className="mono" style={{ fontSize: 18, marginBottom: 8 }}>~</div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Ricerca rapida</div>
              <div className="mono dim" style={{ fontSize: 12 }}>Per linguaggio, zona, attività</div>
            </div>
          )}
        </div>
      )}

      {/* Manual mode */}
      {activeTab === "manual" && showManualMode && (
        <>
          {showSearchTerms && (
            <div>
              <Kicker>search terms *</Kicker>
              <SmartTagInput tags={searchTags} onChange={setSearchTags} />
              <p className="mono dim" style={{ fontSize: 12, marginTop: 6 }}>
                Scrivi linguaggi, framework o tool — li classifichiamo automaticamente.
              </p>
            </div>
          )}

          {showCountry && (
            <div>
              <Kicker>country *</Kicker>
              <select value={country} onChange={(e) => setCountry(e.target.value)} required style={controlStyle}>
                <option value="">Seleziona paese…</option>
                {COUNTRY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          )}

          {showCity && (
            <div>
              <Kicker>city / region (opzionale)</Kicker>
              <input value={city} onChange={(e) => setCity(e.target.value)} placeholder="es. Vercelli, Piemonte, Torino" style={controlStyle} />
            </div>
          )}

          {showMinActivity && (
            <div>
              <Kicker>min activity (mesi)</Kicker>
              <select value={String(minActivity)} onChange={(e) => setMinActivity(Number(e.target.value))} style={controlStyle}>
                <option value="3">3 mesi</option>
                <option value="6">6 mesi</option>
                <option value="12">12 mesi</option>
                <option value="24">24 mesi</option>
              </select>
              <p className="mono dim" style={{ fontSize: 12, marginTop: 6 }}>Ultimo push entro questo periodo.</p>
            </div>
          )}
        </>
      )}

      {/* JD mode */}
      {activeTab === "jd" && showJdMode && showJobDescription && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
            <span className="kicker">job description</span>
            <span className="mono dim" style={{ fontSize: 11 }}>{jobDescription.length} / 4000</span>
          </div>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Incolla qui la job description completa…"
            rows={8}
            style={{ ...controlStyle, minHeight: 160, resize: "vertical", lineHeight: 1.5 }}
            required
          />
          <p className="mono dim" style={{ fontSize: 12, marginTop: 10, lineHeight: 1.55 }}>
            L&apos;AI estrae skill richieste, livello di esperienza e preferenze. Più dettaglio fornisci, migliore è la qualità del match.
          </p>
        </div>
      )}

      {/* Shared: max results */}
      {showMaxResults && (
        <div>
          <Kicker>max results</Kicker>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <input
              type="range"
              min={5}
              max={activeTab === "jd" ? 50 : 20}
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              className="flex-1 appearance-none bg-transparent cursor-pointer [&::-webkit-slider-runnable-track]:h-[2px] [&::-webkit-slider-runnable-track]:bg-[#cfcabd] [&::-webkit-slider-runnable-track]:rounded-full [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#111111] [&::-webkit-slider-thumb]:-mt-[5px]"
            />
            <span className="mono" style={{ fontSize: 18, fontWeight: 700, minWidth: 32, textAlign: "right" }}>{maxResults}</span>
          </div>
        </div>
      )}

      {error && <p className="mono" style={{ fontSize: 13, color: "var(--err, #b00)" }}>{error}</p>}

      <button
        type="submit"
        disabled={loading || !currentUser || !isValid}
        className="btn btn--accent"
        style={{ width: "100%", padding: "14px", fontSize: 15, opacity: loading || !currentUser || !isValid ? 0.5 : 1 }}
      >
        {loading ? "Creo…" : currentUser === undefined ? "Carico…" : "[ avvia ricerca ]"}
      </button>
    </form>
  );
}
