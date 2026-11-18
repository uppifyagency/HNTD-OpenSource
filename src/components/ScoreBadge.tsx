import { Badge } from "@/components/ui/badge";

export function ScoreBadge({ score, size = "sm" }: { score: number | undefined; size?: "sm" | "lg" }) {
  if (score === undefined) {
    return (
      <Badge variant="outline" className="font-mono border-muted-foreground/30 text-muted-foreground">
        unscored
      </Badge>
    );
  }

  const color =
    score >= 70
      ? "border-primary/30 text-primary bg-primary/5"
      : score >= 40
        ? "border-score-amber/30 text-score-amber bg-score-amber/5"
        : "border-destructive/30 text-destructive bg-destructive/5";

  const sizeClass = size === "lg" ? "text-base px-2 py-0.5 sm:text-lg sm:px-3 sm:py-1" : "text-xs";

  return (
    <Badge variant="outline" className={`font-mono ${color} ${sizeClass}`}>
      {score}/100
    </Badge>
  );
}
