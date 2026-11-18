"use client";

import Link from "next/link";
import Image from "next/image";
import { ScoreBadge } from "./ScoreBadge";
import { FavoriteButton } from "./FavoriteButton";
import { SocialProof } from "./SocialProof";
import { Doc } from "../../convex/_generated/dataModel";

export function DeveloperCard({
  developer,
  showMatchConfidence = false,
  showNormalizedScore = false,
  isPass2 = false,
  viewCount = 0,
  saveCount = 0,
  taskId,
  visibilityOverrides,
}: {
  developer: Doc<"developers">;
  showMatchConfidence?: boolean;
  showNormalizedScore?: boolean;
  isPass2?: boolean;
  viewCount?: number;
  saveCount?: number;
  taskId?: string;
  visibilityOverrides?: {
    showAvatar?: boolean;
    showScore?: boolean;
    showMatchConfidenceBar?: boolean;
    showLanguages?: boolean;
    showJdBreakdown?: boolean;
    showScoreBreakdown?: boolean;
    showActivity?: boolean;
  };
}) {
  const vis = {
    showAvatar: visibilityOverrides?.showAvatar ?? true,
    showScore: visibilityOverrides?.showScore ?? true,
    showMatchConfidenceBar: visibilityOverrides?.showMatchConfidenceBar ?? true,
    showLanguages: visibilityOverrides?.showLanguages ?? true,
  };

  const matchBarColor =
    (developer.matchConfidence ?? 0) >= 70
      ? "hsl(var(--ok))"
      : (developer.matchConfidence ?? 0) >= 40
        ? "hsl(var(--warn))"
        : "hsl(var(--err))";

  // Color for the JD matchConfidence percentage (thresholds 70/40, same as the bar)
  const matchCls =
    (developer.matchConfidence ?? 0) >= 70
      ? "text-ok"
      : (developer.matchConfidence ?? 0) >= 40
        ? "text-warn"
        : "text-err";

  const score = showNormalizedScore && developer.normalizedScore != null
    ? developer.normalizedScore
    : developer.score;

  return (
    <div
      className="rounded-lg border transition-colors border-border bg-card"
    >
      {/* BODY -- clickable area navigates to profile */}
      <Link
        href={`/dashboard/developer/${developer._id}${taskId ? `?taskId=${taskId}` : ""}`}
        className="block px-4 pt-3.5 pb-2 hover:border-primary/30 transition-colors"
      >
        {/* ROW 1: Avatar + Name + Score badge */}
        <div className="flex items-start gap-3">
          {vis.showAvatar && (developer.avatarUrl ? (
            <Image
              src={developer.avatarUrl}
              alt={developer.login}
              width={48}
              height={48}
              className="w-12 h-12 rounded-full border border-border shrink-0"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-muted border border-border flex items-center justify-center font-mono text-primary text-base shrink-0">
              {developer.login[0]?.toUpperCase()}
            </div>
          ))}

          <div className="flex-1 min-w-0">
            {/* Name row: name + social proof + score */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="font-mono text-[15px] text-foreground font-semibold truncate">
                  {developer.name || developer.login}
                </span>
                {(viewCount > 0 || saveCount > 0) && (
                  <SocialProof viewCount={viewCount} saveCount={saveCount} />
                )}
              </div>
              {vis.showScore && (
                <ScoreBadge score={score} />
              )}
            </div>

            {/* Meta line: Location + Languages */}
            <div className="flex items-center gap-1.5 mt-0.5">
              {developer.location && (
                <span className="font-mono text-[13px] text-muted-foreground shrink-0">
                  {developer.location}
                </span>
              )}
              {developer.location && vis.showLanguages && developer.topLanguages.length > 0 && (
                <span className="font-mono text-[13px] text-muted-foreground shrink-0">·</span>
              )}
              {vis.showLanguages && (
                <span className="font-mono text-[12px] text-muted-foreground truncate min-w-0">
                  {developer.topLanguages.slice(0, 3).join(", ")}
                </span>
              )}
            </div>

            {/* Summary text -- 2-line clamp */}
            {developer.matchReason && showMatchConfidence ? (
              <p className="font-mono text-[13px] text-muted-foreground/80 mt-1.5 line-clamp-2 leading-snug">
                {developer.matchReason}
              </p>
            ) : showNormalizedScore && developer.rankComment ? (
              <p className="font-mono text-[13px] text-muted-foreground/80 mt-1.5 italic line-clamp-2 leading-snug">
                {developer.rankComment}
              </p>
            ) : null}
          </div>
        </div>
      </Link>

      {/* FOOTER */}
      <div className="border-t border-border/50">
        {/* Match bar row — compact: percentage + bar */}
        {vis.showMatchConfidenceBar && showMatchConfidence && developer.matchConfidence != null && (
          <div className="flex items-center gap-3 px-4 h-9">
            <span className={`font-mono text-xs font-semibold ${matchCls} shrink-0`}>
              {developer.matchConfidence}%
            </span>
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${developer.matchConfidence}%`, backgroundColor: matchBarColor }}
              />
            </div>
          </div>
        )}

        {/* Actions row: Save + GitHub */}
        <div className={`flex items-center gap-2 px-4 h-10 ${vis.showMatchConfidenceBar && showMatchConfidence && developer.matchConfidence != null ? "border-t border-border/50" : ""}`}>
          <div onClick={(e) => e.preventDefault()}>
            <FavoriteButton developerId={developer._id} size="lg" />
          </div>
          <a
            href={developer.profileUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="ml-auto font-mono text-sm font-semibold text-foreground hover:text-primary transition-colors whitespace-nowrap"
          >
            GitHub &rarr;
          </a>
        </div>
      </div>
    </div>
  );
}
