"use client";

import { useMutation, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { Id } from "../../convex/_generated/dataModel";

export function FavoriteButton({
  developerId,
  size = "sm",
}: {
  developerId: Id<"developers">;
  size?: "sm" | "lg";
}) {
  const favorites = useQuery(api.favorites.getByUser);
  const toggle = useMutation(api.favorites.toggle);

  const isSaved = favorites?.some((f) => f.developerId === developerId) ?? false;

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggle({ developerId });
  };

  if (size === "lg") {
    return (
      <button
        onClick={handleClick}
        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 font-mono text-xs whitespace-nowrap transition-colors cursor-pointer ${
          isSaved
            ? "border-primary/30 text-primary"
            : "border-border text-muted-foreground hover:border-primary/30"
        }`}
      >
        <span>{isSaved ? "♥" : "♡"}</span>
        {isSaved ? "In pipeline" : "Save to pipeline"}
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={`text-sm transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center ${
        isSaved ? "text-primary" : "text-muted-foreground hover:text-primary"
      }`}
      title={isSaved ? "Remove from pipeline" : "Save to pipeline"}
    >
      {isSaved ? "♥" : "♡"}
    </button>
  );
}
