"use client";

import { Doc } from "../../convex/_generated/dataModel";
import { exportCsv } from "@/lib/exportCsv";
import type { ExportSortKey } from "@/lib/taskResults/taskResultsViewModel";
import { Button } from "@/components/ui/button";

export function ExportButtons({
  developers,
  title,
  filename,
  sortBy = "objectiveScore",
}: {
  developers: Doc<"developers">[];
  title: string;
  filename: string;
  /** Print-only: which number goes on the PDF badge. `developers` must already be in
   *  on-screen order — neither export re-sorts. */
  sortBy?: ExportSortKey;
}) {
  const handlePdf = async () => {
    const { exportPdf } = await import("@/lib/exportPdf");
    exportPdf(developers, title, filename, sortBy);
  };

  return (
    <div className="flex gap-2">
      <Button
        variant="outline"
        onClick={() => exportCsv(developers, filename)}
        className="font-mono text-xs cursor-pointer"
      >
        CSV
      </Button>
      <Button
        variant="outline"
        onClick={handlePdf}
        className="font-mono text-xs cursor-pointer"
      >
        PDF
      </Button>
    </div>
  );
}
