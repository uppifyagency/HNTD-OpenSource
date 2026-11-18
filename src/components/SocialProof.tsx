export function SocialProof({
  viewCount,
  saveCount,
}: {
  viewCount: number;
  saveCount: number;
}) {
  if (viewCount === 0 && saveCount === 0) return null;

  return (
    <span className="font-mono text-xs text-muted-foreground">
      {viewCount > 0 && <span>◉ {viewCount}</span>}
      {viewCount > 0 && saveCount > 0 && <span className="mx-1.5">·</span>}
      {saveCount > 0 && <span>♥ {saveCount}</span>}
    </span>
  );
}
