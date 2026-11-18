/**
 * SkeletonCard — shimmer placeholder matching developer card shape.
 * Uses Tailwind animate-pulse on bg-muted elements.
 */
export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      {/* Avatar + name lines */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-muted animate-pulse shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-muted rounded animate-pulse w-3/5" />
          <div className="h-3 bg-muted rounded animate-pulse w-2/5" />
        </div>
      </div>
      {/* Body lines */}
      <div className="space-y-2">
        <div className="h-3 bg-muted rounded animate-pulse w-full" />
        <div className="h-3 bg-muted rounded animate-pulse w-4/5" />
      </div>
    </div>
  );
}

/** Renders a grid of 3 skeleton cards for loading states. */
export function SkeletonCardGroup({ count = 3 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
