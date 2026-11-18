"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useMutation } from "convex/react";
import { api } from "../../convex/_generated/api";
import { Doc } from "../../convex/_generated/dataModel";
import { ScoreBadge } from "./ScoreBadge";
import { useVisibility } from "@/hooks/useVisibility";

const STATUSES = ["saved", "contacted", "interviewing", "rejected"] as const;
type Status = (typeof STATUSES)[number];

const STATUS_LABELS: Record<Status, string> = {
  saved: "Saved",
  contacted: "Contacted",
  interviewing: "Interviewing",
  rejected: "Rejected",
};

export function KanbanCard({
  favorite,
  developer,
}: {
  favorite: Doc<"favorites">;
  developer: Doc<"developers"> | null;
}) {
  const updateStatus = useMutation(api.favorites.updateStatus);
  const removeFav = useMutation(api.favorites.remove);
  const [showMenu, setShowMenu] = useState(false);
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [note, setNote] = useState("");
  const showAvatar = useVisibility("pipeline.kanbanCard.avatar");
  const showScore = useVisibility("pipeline.kanbanCard.score");
  const showHrSummary = useVisibility("pipeline.kanbanCard.hrSummary");
  const showLanguages = useVisibility("pipeline.kanbanCard.languages");
  const showNote = useVisibility("pipeline.kanbanCard.note");

  if (!developer) return null;

  const otherStatuses = STATUSES.filter((s) => s !== favorite.status);

  const handleMove = async (newStatus: Status) => {
    if (newStatus === "rejected") {
      setShowNoteInput(true);
      setShowMenu(false);
      return;
    }
    await updateStatus({ favoriteId: favorite._id, status: newStatus });
    setShowMenu(false);
  };

  const handleReject = async () => {
    await updateStatus({
      favoriteId: favorite._id,
      status: "rejected",
      note: note.trim() || undefined,
    });
    setShowNoteInput(false);
    setNote("");
  };

  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-3 hover:border-primary/30 transition-colors">
      <Link
        href={`/dashboard/developer/${developer._id}`}
        className="block hover:opacity-80 transition-opacity"
      >
        {/* Header */}
        <div className="flex items-start gap-3 mb-3">
          {showAvatar && (developer.avatarUrl ? (
            <Image
              src={developer.avatarUrl}
              alt={developer.login}
              width={48}
              height={48}
              className="w-12 h-12 rounded-full border border-border"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-muted border border-border flex items-center justify-center font-mono text-primary text-lg">
              {developer.login[0]?.toUpperCase()}
            </div>
          ))}
          <div className="flex-1 min-w-0">
            <p className="font-mono text-sm font-bold text-foreground truncate">
              {developer.name || developer.login}
            </p>
            {developer.location && (
              <p className="font-mono text-xs text-muted-foreground truncate">
                {developer.location}
              </p>
            )}
          </div>
          {showScore && <ScoreBadge score={developer.score} />}
        </div>

        {/* HR Summary */}
        {showHrSummary && developer.hrSummary && (
          <p className="font-mono text-xs text-foreground/80 leading-relaxed mb-3 line-clamp-2">
            {developer.hrSummary}
          </p>
        )}

        {/* Languages */}
        {showLanguages && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {developer.topLanguages.slice(0, 4).map((lang) => (
              <span
                key={lang}
                className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                {lang}
              </span>
            ))}
          </div>
        )}
      </Link>

      {showNote && favorite.note && (
        <p className="font-mono text-xs text-muted-foreground italic truncate">
          {favorite.note}
        </p>
      )}

      {showNoteInput ? (
        <div className="space-y-1">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleReject()}
            placeholder="Reason (optional)..."
            className="w-full rounded border border-border bg-background px-2 py-2.5 sm:py-1 font-mono text-[10px] text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
            autoFocus
          />
          <div className="flex gap-1">
            <button
              onClick={handleReject}
              className="flex-1 rounded bg-destructive/10 px-2 min-h-[44px] py-2.5 sm:py-1 sm:min-h-0 font-mono text-[10px] text-destructive hover:bg-destructive/20 cursor-pointer"
            >
              Reject
            </button>
            <button
              onClick={() => { setShowNoteInput(false); setNote(""); }}
              className="flex-1 rounded bg-muted px-2 min-h-[44px] py-2.5 sm:py-1 sm:min-h-0 font-mono text-[10px] text-muted-foreground hover:text-foreground cursor-pointer"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="w-full rounded bg-muted px-2 min-h-[44px] py-2.5 sm:py-1 sm:min-h-0 font-mono text-[10px] text-muted-foreground hover:text-foreground cursor-pointer text-left"
          >
            Move to...
          </button>
          {showMenu && (
            <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-border bg-white shadow-lg z-50">
              {otherStatuses.map((s) => (
                <button
                  key={s}
                  onClick={() => handleMove(s)}
                  className="block w-full px-3 min-h-[44px] py-2.5 sm:py-1.5 sm:min-h-0 text-left font-mono text-[10px] text-foreground hover:bg-muted cursor-pointer first:rounded-t-lg"
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
              <button
                onClick={() => { removeFav({ favoriteId: favorite._id }); setShowMenu(false); }}
                className="block w-full px-3 min-h-[44px] py-2.5 sm:py-1.5 sm:min-h-0 text-left font-mono text-[10px] text-destructive hover:bg-destructive/5 cursor-pointer rounded-b-lg border-t border-border"
              >
                Remove from pipeline
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
