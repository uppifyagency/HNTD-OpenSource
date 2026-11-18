"use client";

import Image from "next/image";
import { ScoreBadge } from "./ScoreBadge";
import { Doc } from "../../convex/_generated/dataModel";
import { FavoriteButton } from "./FavoriteButton";
import { HireabilityBadge } from "./HireabilityBadge";
import { useVisibility } from "@/hooks/useVisibility";

function barColorClass(pct: number): string {
  if (pct >= 0.70) return "bg-ok";
  if (pct >= 0.40) return "bg-warn";
  return "bg-err";
}

function matchLabel(confidence: number): { text: string; colorClass: string; dotClass: string } {
  if (confidence >= 70) return { text: "Strong Match", colorClass: "text-ok", dotClass: "bg-ok" };
  if (confidence >= 40) return { text: "Good Match", colorClass: "text-warn", dotClass: "bg-warn" };
  return { text: "Weak Match", colorClass: "text-err", dotClass: "bg-err" };
}

export function DeveloperProfile({ developer, showJdAnalysis = false, jdRubric }: { developer: Doc<"developers">; showJdAnalysis?: boolean; jdRubric?: Record<string, number> }) {
  const bd = developer.scoreBreakdown;
  // BUG-06: undefined (not 0) when no score data — ScoreBadge shows "unscored"
  const objScore = developer.objectiveScore ??
    (bd ? bd.codeQuality + bd.architecture + bd.testing + bd.documentation + bd.complexity + bd.consistency : undefined);
  const showHeader = useVisibility("devProfile.header");
  const showObjectiveScore = useVisibility("devProfile.header.objectiveScore");
  const showMatchConfidence = useVisibility("devProfile.header.matchConfidence");
  const showLocation = useVisibility("devProfile.header.location");
  const showCompany = useVisibility("devProfile.header.company");
  const showHireable = useVisibility("devProfile.header.hireable");
  const showBio = useVisibility("devProfile.bio");
  const showAiAssessment = useVisibility("devProfile.aiAssessment");
  const showJdFitAssessment = useVisibility("devProfile.jdFitAssessment");
  const showJdScoreBreakdown = useVisibility("devProfile.jdScoreBreakdown");
  const showScoreBreakdown = useVisibility("devProfile.scoreBreakdown");
  const showCodeQuality = useVisibility("devProfile.scoreBreakdown.codeQuality");
  const showArchitecture = useVisibility("devProfile.scoreBreakdown.architecture");
  const showTesting = useVisibility("devProfile.scoreBreakdown.testing");
  const showDocumentation = useVisibility("devProfile.scoreBreakdown.documentation");
  const showComplexity = useVisibility("devProfile.scoreBreakdown.complexity");
  const showConsistency = useVisibility("devProfile.scoreBreakdown.consistency");
  const showGithubActivity = useVisibility("devProfile.githubActivity");
  const showCommits = useVisibility("devProfile.githubActivity.commits");
  const showPrs = useVisibility("devProfile.githubActivity.prs");
  const showReviews = useVisibility("devProfile.githubActivity.reviews");
  const showActiveDays = useVisibility("devProfile.githubActivity.activeDays");
  const showSocialAccounts = useVisibility("devProfile.socialAccounts");
  const showRankingBreakdown = useVisibility("devProfile.rankingBreakdown");
  const showPinnedRepos = useVisibility("devProfile.pinnedRepos");
  const showLanguages = useVisibility("devProfile.languages");
  const showTopRepos = useVisibility("devProfile.topRepos");

  return (
    <div className="space-y-4">
      {/* ── HERO CARD — V4 layout: name+buttons top row, match below, signals below, tags below ── */}
      {showHeader && (
        <div className="rounded-lg border border-border bg-card p-6">
          {/* HEADER: Avatar + Name/meta */}
          <div className="flex items-start gap-4">
            {developer.avatarUrl ? (
              <Image
                src={developer.avatarUrl}
                alt={developer.login}
                width={72}
                height={72}
                className="w-[72px] h-[72px] rounded-full border border-border shrink-0"
              />
            ) : (
              <div className="w-[72px] h-[72px] rounded-full bg-muted border border-border flex items-center justify-center font-mono text-foreground text-2xl shrink-0">
                {developer.login[0]?.toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h1 className="text-xl font-semibold text-foreground truncate">
                    {developer.name || developer.login}
                  </h1>
                  <p className="font-mono text-[13px] text-muted-foreground mt-0.5">
                    @{developer.login}
                  </p>
                  <p className="font-mono text-[13px] text-muted-foreground mt-0.5">
                    {showCompany && developer.company && <>{developer.company}</>}
                    {showCompany && developer.company && showLocation && developer.location && <> &middot; </>}
                    {showLocation && developer.location && <>{developer.location}</>}
                  </p>
                </div>
                {/* Desktop-only inline buttons */}
                <div className="hidden sm:flex items-center gap-2 shrink-0">
                  <FavoriteButton developerId={developer._id} size="lg" />
                  <a
                    href={developer.profileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-lg border border-border bg-card px-3 py-1.5 font-mono text-sm font-semibold text-foreground hover:border-muted-foreground/30 transition-colors whitespace-nowrap"
                  >
                    View GitHub
                  </a>
                  {developer.email && (
                    <a
                      href={`mailto:${developer.email}`}
                      className="rounded-lg border border-border bg-card px-3 py-1.5 font-mono text-sm text-foreground hover:border-muted-foreground/30 transition-colors truncate max-w-[200px]"
                    >
                      {developer.email}
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* FULL-WIDTH CONTENT below header */}

          {/* Match badge — immediately after header (most important signal) */}
          {showMatchConfidence && showJdAnalysis && developer.matchConfidence != null && (() => {
            const m = matchLabel(developer.matchConfidence);
            return (
              <div className="mt-4">
                <span className={`inline-flex items-center gap-2 border border-border rounded-lg px-3 py-1.5 font-mono text-xs font-semibold ${m.colorClass}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${m.dotClass}`} />
                  {m.text}
                </span>
              </div>
            );
          })()}

          {/* Hireability badge — self-declared GitHub "Available for hire" + company context */}
          {showHireable && (
            <div className="mt-3">
              <HireabilityBadge hireable={developer.hireable} company={developer.company} />
            </div>
          )}

          {/* Mobile-only action buttons — full-width, 44px touch targets */}
          <div className="flex sm:hidden gap-2 mt-4">
            <FavoriteButton developerId={developer._id} size="lg" />
            <a
              href={developer.profileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-center rounded-lg border border-border bg-card px-3 min-h-[44px] flex items-center justify-center font-mono text-sm font-semibold text-foreground hover:border-muted-foreground/30 transition-colors"
            >
              View GitHub
            </a>
          </div>
          {/* Mobile-only email — separate full-width row, 44px */}
          {developer.email && (
            <div className="sm:hidden mt-2">
              <a
                href={`mailto:${developer.email}`}
                className="block w-full text-center rounded-lg border border-border bg-card px-3 min-h-[44px] leading-[44px] font-mono text-sm text-foreground hover:border-muted-foreground/30 transition-colors"
              >
                {developer.email}
              </a>
            </div>
          )}

          {/* Signal pills — GitHub metrics */}
          <div className="flex flex-wrap gap-1.5 mt-4">
            {developer.totalCommitContributions != null && (
              <span className="inline-flex items-center gap-1 border border-border rounded px-2.5 py-1 font-mono text-xs text-muted-foreground">
                <span className="w-[5px] h-[5px] rounded-full bg-ok shrink-0" />
                {developer.totalCommitContributions >= 1000 ? `${(developer.totalCommitContributions / 1000).toFixed(0)}K+` : developer.totalCommitContributions} commits
              </span>
            )}
            {developer.topRepos && (() => {
              const stars = developer.topRepos.reduce((s, r) => s + (r.stars ?? 0), 0);
              return stars > 0 ? (
                <span className="inline-flex items-center gap-1 border border-border rounded px-2.5 py-1 font-mono text-xs text-muted-foreground">
                  <span className="w-[5px] h-[5px] rounded-full bg-ok shrink-0" />
                  {stars >= 1000 ? `${(stars / 1000).toFixed(0)}K+` : stars} stars
                </span>
              ) : null;
            })()}
            {developer.lastPushAt && (
              <span className="inline-flex items-center gap-1 border border-border rounded px-2.5 py-1 font-mono text-xs text-muted-foreground">
                <span className={`w-[5px] h-[5px] rounded-full shrink-0 ${Math.floor((Date.now() - developer.lastPushAt) / 86400000) <= 30 ? "bg-ok" : "bg-warn"}`} />
                Last active {Math.floor((Date.now() - developer.lastPushAt) / 86400000)}d ago
              </span>
            )}
          </div>

          {/* Language + domain tags */}
          {showLanguages && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {developer.topLanguages?.slice(0, 3).map((lang) => (
                <span key={lang} className="border border-border rounded px-2.5 py-1 font-mono text-xs text-muted-foreground">
                  {lang}
                </span>
              ))}
              {developer.topRepos?.slice(0, 3).filter(r => r.topics && r.topics.length > 0).flatMap(r => r.topics!).filter((t, i, a) => a.indexOf(t) === i && !developer.topLanguages?.map(l => l.toLowerCase()).includes(t.toLowerCase())).slice(0, 4).map((topic) => (
                <span key={topic} className="border border-border rounded px-2.5 py-1 font-mono text-xs text-muted-foreground">
                  {topic}
                </span>
              ))}
            </div>
          )}

          {/* HR "Why this candidate" box */}
          {showAiAssessment && developer.scoreComment && (
            <div className="bg-muted rounded-lg p-4 mt-4">
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                Why This Candidate
              </p>
              <p className="font-mono text-sm text-secondary-foreground leading-relaxed">
                {developer.scoreComment}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Bio removed in V4 — scoreComment in hero "Why This Candidate" replaces it */}

      {/* ── TWO-COLUMN DETAIL GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Row 1 Left: JD Fit Assessment */}
        {showJdFitAssessment && developer.jdAssessment && (
          <div className="rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Job Fit Assessment
            </p>
            <p className="font-mono text-sm text-secondary-foreground leading-relaxed">
              {developer.jdAssessment}
            </p>
          </div>
        )}

        {/* Row 1 Left: JD Score Breakdown (if no jdAssessment text, this takes left slot) */}
        {showJdScoreBreakdown && developer.jdScoreBreakdown && (() => {
          const jdBd = developer.jdScoreBreakdown as Record<string, number>;
          const entries = Object.entries(jdBd).sort(([, a], [, b]) => b - a);
          return (
            <div className="rounded-lg border border-border bg-card p-5">
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
                JD Score Breakdown
              </p>
              <div className="space-y-2.5">
                {entries.map(([label, value]) => {
                  const max = jdRubric?.[label] ?? Math.max(...entries.map(([, v]) => v));
                  const pct = value / max;
                  return (
                    <div key={label} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[13px] text-muted-foreground truncate">{label}</span>
                        <span className="font-mono text-[13px] text-foreground text-right">{value}/{max}</span>
                      </div>
                      <div className="h-1 bg-faint rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${barColorClass(pct)}`}
                          style={{ width: `${pct * 100}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}

        {/* Row 1 Right: Technical Assessment (Score Breakdown) */}
        {showScoreBreakdown && developer.scoreBreakdown && (
          <div className="rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Technical Assessment
            </p>
            <div className="space-y-2.5">
              {[
                { label: "Code Quality", value: developer.scoreBreakdown.codeQuality, max: 20, show: showCodeQuality },
                { label: "Architecture", value: developer.scoreBreakdown.architecture, max: 20, show: showArchitecture },
                { label: "Testing", value: developer.scoreBreakdown.testing, max: 15, show: showTesting },
                { label: "Documentation", value: developer.scoreBreakdown.documentation, max: 15, show: showDocumentation },
                { label: "Complexity", value: developer.scoreBreakdown.complexity, max: 15, show: showComplexity },
                { label: "Consistency", value: developer.scoreBreakdown.consistency, max: 15, show: showConsistency },
              ].filter((cat) => cat.show).map((cat) => {
                const pct = cat.value / cat.max;
                return (
                  <div key={cat.label} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[13px] text-muted-foreground">{cat.label}</span>
                      <span className="font-mono text-[13px] text-foreground text-right">
                        {cat.value}/{cat.max}
                      </span>
                    </div>
                    <div className="h-1 bg-faint rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${barColorClass(pct)}`}
                        style={{ width: `${pct * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              {/* Total row */}
              {objScore !== undefined && (
                <div className="flex justify-end pt-2.5 border-t border-border mt-2.5">
                  <span className="font-mono text-sm font-bold text-foreground">
                    {objScore}<span className="text-muted-foreground font-normal">/100</span>
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Row 2 Left: Activity */}
        {showGithubActivity && (developer.totalCommitContributions != null || developer.contributionDays != null) && (
          <div className="rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Activity
            </p>
            <div className="grid grid-cols-2 gap-4 mb-4">
              {showCommits && developer.totalCommitContributions != null && (
                <div>
                  <p className="font-mono text-xl font-bold text-foreground">{developer.totalCommitContributions.toLocaleString()}</p>
                  <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Commits</p>
                </div>
              )}
              {showPrs && developer.totalPullRequestContributions != null && (
                <div>
                  <p className="font-mono text-xl font-bold text-foreground">{developer.totalPullRequestContributions.toLocaleString()}</p>
                  <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Pull Requests</p>
                </div>
              )}
              {showReviews && developer.totalPullRequestReviewContributions != null && (
                <div>
                  <p className="font-mono text-xl font-bold text-foreground">{developer.totalPullRequestReviewContributions.toLocaleString()}</p>
                  <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Code Reviews</p>
                </div>
              )}
              {showActiveDays && developer.contributionDays != null && (
                <div>
                  <p className="font-mono text-xl font-bold text-foreground">{developer.contributionDays}</p>
                  <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Active Days</p>
                </div>
              )}
            </div>

            {/* Account metrics pills — V4 shows followers, repos, achievements */}
            <div className="flex gap-2 flex-wrap">
              {developer.followers != null && developer.followers > 0 && (
                <span className="font-mono text-xs border border-border rounded px-2.5 py-1 text-muted-foreground">
                  {developer.followers >= 1000 ? `${(developer.followers / 1000).toFixed(1)}K` : developer.followers} followers
                </span>
              )}
              {developer.publicRepos != null && developer.publicRepos > 0 && (
                <span className="font-mono text-xs border border-border rounded px-2.5 py-1 text-muted-foreground">
                  {developer.publicRepos} repos
                </span>
              )}
              {developer.isGitHubStar && (
                <span className="font-mono text-xs border border-border rounded px-2.5 py-1 text-muted-foreground">
                  GitHub Star
                </span>
              )}
              {developer.isDeveloperProgramMember && (
                <span className="font-mono text-xs bg-purple-100 text-purple-700 rounded px-2.5 py-1">
                  Dev Program
                </span>
              )}
              {developer.hasSponsorsListing && (
                <span className="font-mono text-xs border border-border rounded px-2.5 py-1 text-muted-foreground">
                  Sponsors
                </span>
              )}
            </div>
          </div>
        )}

        {/* Row 2 Right: Candidate Ranking */}
        {showRankingBreakdown && developer.deterministicRank != null && (
          <div className="rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Candidate Ranking
            </p>
            <div className="space-y-2.5">
              {[
                { label: "Skill Match", value: developer.languageFitScore },
                { label: "Team Player", value: developer.collaborationScore },
                { label: "Code Quality", value: developer.objectiveScore },
                { label: "Experience", value: developer.projectMaturityScore },
              ].map((dim) => {
                // UI-10: a missing sub-score means "not measured", not 0
                const missing = dim.value == null;
                const pct = missing ? 0 : dim.value! / 100;
                return (
                  <div key={dim.label} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[13px] text-muted-foreground">
                        {dim.label}
                      </span>
                      <span className={`font-mono text-[13px] text-right ${missing ? "text-muted-foreground" : "text-foreground"}`}>
                        {missing ? "—" : Math.round(dim.value!)}
                      </span>
                    </div>
                    <div className="h-1 bg-faint rounded-full overflow-hidden">
                      {!missing && (
                        <div
                          className={`h-full rounded-full transition-all ${barColorClass(pct)}`}
                          style={{ width: `${dim.value}%` }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Pinned Repos — full-width */}
        {showPinnedRepos && developer.pinnedRepos && developer.pinnedRepos.length > 0 && (
          <div className="md:col-span-2 rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Pinned Repositories
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {developer.pinnedRepos.map((repo) => (
                <div
                  key={repo.name}
                  className="rounded-lg border border-border p-3"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-sm text-primary font-semibold">{repo.name}</span>
                    <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                      {repo.primaryLanguage && <span>{repo.primaryLanguage}</span>}
                      {repo.stars != null && <span>{repo.stars} stars</span>}
                    </div>
                  </div>
                  {repo.description && (
                    <p className="font-mono text-xs text-muted-foreground truncate">{repo.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key Projects (Top Repos) — full-width */}
        {showTopRepos && (
          <div className="md:col-span-2 rounded-lg border border-border bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Key Projects
            </p>
            <div className="divide-y divide-border">
              {developer.topRepos.map((repo) => (
                <a
                  key={repo.name}
                  href={repo.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 py-3 first:pt-0 last:pb-0 hover:opacity-80 transition-opacity"
                >
                  <div className="flex-1 min-w-0">
                    <span className="font-mono text-sm font-semibold text-foreground">{repo.name}</span>
                    {repo.description && (
                      <p className="font-mono text-[10px] text-muted-foreground mt-0.5 truncate">{repo.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 font-mono text-xs text-muted-foreground shrink-0">
                    {repo.language && <span>{repo.language}</span>}
                    <span>{repo.stars.toLocaleString()} stars</span>
                    <span>{repo.forks.toLocaleString()} forks</span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
