import { Doc } from "../../convex/_generated/dataModel";

/**
 * `developers` MUST already be in the order the recruiter is looking at — the caller builds it
 * from the leaderboard view model. This function does NOT re-sort.
 *
 * It used to, with its own `b[sortBy] ?? b.score` fallback chain, and that is how finding #8
 * survived its first fix: the screen and the file each computed their own ranking value, so a
 * developer with no matchConfidence sorted last on screen (value 0) and near the top of the
 * file (value = raw `score`) — two incommensurable quantities compared as one. Re-deriving an
 * order here can only ever disagree with the single definition in taskResultsViewModel.
 */
export function exportCsv(developers: Doc<"developers">[], filename: string) {
  const headers = [
    "Name", "Login", "Location", "Languages",
    "Objective Score", "Calibrated Score", "Composite Score", "Raw Scorer Score",
    "Match%", "Email", "GitHub URL", "HR Summary",
  ];

  const rows = developers.map((d) => [
    d.name || d.login,
    d.login,
    d.location || "",
    d.topLanguages.join("; "),
    d.objectiveScore?.toString() ?? "",
    d.normalizedScore?.toString() ?? "",
    // Was missing entirely: in the default "Calibrated" mode the file was ordered by a number
    // that appeared nowhere in it.
    d.compositeScore?.toString() ?? "",
    // Header used to read "JD Score", which is a lie for a manual-mode task: this is the
    // scorer's raw output, and it is also what the screen's "objective" headline falls back to.
    d.score?.toString() ?? "",
    d.matchConfidence?.toString() ?? "",
    d.email || "",
    d.profileUrl,
    (d.hrSummary || "").replace(/"/g, '""'),
  ]);

  const csvContent = [
    headers.join(","),
    ...rows.map((row) =>
      row.map((cell) => `"${cell}"`).join(",")
    ),
  ].join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
