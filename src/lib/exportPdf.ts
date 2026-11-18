import jsPDF from "jspdf";
import { Doc } from "../../convex/_generated/dataModel";
import { BADGE_LABEL, type ExportSortKey } from "./taskResults/taskResultsViewModel";

// ── Typographic constants ──────────────────────────────────
const PAGE = { unit: "mm" as const, format: "a4" as const };
const MARGIN = { top: 20, bottom: 20, left: 22, right: 22 };
const FONT = "courier";

// Vertical rhythm: all spacing is a multiple of 3.5mm
const RHYTHM = 3.5;
const LINE = {
  name: 12,       // developer name
  login: 8.5,     // @username
  meta: 7.5,      // location, languages
  body: 7.5,      // HR summary
  url: 6.5,       // github url
  footer: 7,      // page footer
  header: 13,     // HNTD INTEL
  headerSub: 8,   // date + title
};

const COLOR = {
  black: [20, 20, 20] as const,
  dark: [60, 60, 60] as const,
  mid: [110, 110, 110] as const,
  light: [160, 160, 160] as const,
  rule: [210, 210, 210] as const,
  scoreHigh: [34, 160, 80] as const,
  scoreMid: [200, 140, 20] as const,
  scoreLow: [200, 70, 60] as const,
};

export function exportPdf(
  developers: Doc<"developers">[],
  title: string,
  filename: string,
  // Print-only: it selects WHICH number goes on the badge. It must never re-order, because
  // `developers` already carries the recruiter's on-screen order.
  sortBy: ExportSortKey = "objectiveScore"
) {
  const doc = new jsPDF(PAGE);
  const pw = doc.internal.pageSize.getWidth();
  const ph = doc.internal.pageSize.getHeight();
  const cw = pw - MARGIN.left - MARGIN.right;
  let y = MARGIN.top;
  let pageNum = 1;

  // ── Helpers ────────────────────────────────────────────
  function setColor(c: readonly [number, number, number]) {
    doc.setTextColor(c[0], c[1], c[2]);
  }

  function scoreColor(score: number) {
    if (score >= 70) return COLOR.scoreHigh;
    if (score >= 45) return COLOR.scoreMid;
    return COLOR.scoreLow;
  }

  function needsNewPage(blockHeight: number) {
    return y + blockHeight > ph - MARGIN.bottom - 12;
  }

  // ── Page furniture ─────────────────────────────────────
  function addHeader() {
    // Brand
    doc.setFont(FONT, "bold");
    doc.setFontSize(LINE.header);
    setColor(COLOR.black);
    doc.text("HNTD INTEL", MARGIN.left, y);

    // Date + title, right-aligned
    doc.setFont(FONT, "normal");
    doc.setFontSize(LINE.headerSub);
    setColor(COLOR.mid);
    const dateStr = new Date().toLocaleDateString("en-GB", {
      day: "2-digit", month: "2-digit", year: "numeric",
    });
    doc.text(`${dateStr}  —  ${title}`, pw - MARGIN.right, y, { align: "right" });

    // Rule
    y += RHYTHM + 1;
    doc.setDrawColor(COLOR.rule[0], COLOR.rule[1], COLOR.rule[2]);
    doc.setLineWidth(0.3);
    doc.line(MARGIN.left, y, pw - MARGIN.right, y);
    y += RHYTHM * 2;
  }

  function addFooter() {
    doc.setFont(FONT, "normal");
    doc.setFontSize(LINE.footer);
    setColor(COLOR.light);
    doc.text(
      `HNTD INTEL  —  page ${pageNum}`,
      pw / 2,
      ph - MARGIN.bottom + 4,
      { align: "center" }
    );
  }

  function newPage() {
    addFooter();
    doc.addPage();
    pageNum++;
    y = MARGIN.top;
    addHeader();
  }

  // ── Estimate block height for a developer ──────────────
  function estimateBlock(dev: Doc<"developers">) {
    let h = 0;
    h += 6;                         // name line
    h += RHYTHM;                    // @login
    if (dev.location) h += RHYTHM;  // location
    h += RHYTHM;                    // languages
    h += RHYTHM;                    // gap before summary
    if (dev.hrSummary) {
      doc.setFont(FONT, "normal");
      doc.setFontSize(LINE.body);
      const lines = doc.splitTextToSize(dev.hrSummary, cw - 16);
      h += Math.min(lines.length, 3) * RHYTHM;
    }
    h += RHYTHM;                    // url
    h += RHYTHM * 2;               // bottom breathing + rule
    return h;
  }

  // ── Render ─────────────────────────────────────────────
  // NOT re-sorted: `developers` arrives in the recruiter's on-screen order. The previous
  // re-sort used its own `?? score` fallback and could print a non-monotone badge sequence —
  // finding #8's exact signature, reproduced inside the PDF.
  addHeader();

  developers.forEach((dev, i) => {
    const blockH = estimateBlock(dev);
    if (needsNewPage(blockH)) newPage();

    const blockTop = y;

    // ── Score badge (right-aligned, top of block) ────────
    // Reads ONLY the ranked field, with no cross-unit fallback: printing objectiveScore for a
    // developer who has no matchConfidence would put two different units in one column, on the
    // same 70/45 colour scale. Absent → no badge, which is honest.
    const displayScore = dev[sortBy] ?? undefined;
    if (displayScore !== undefined) {
      const sc = scoreColor(displayScore);
      const badgeX = pw - MARGIN.right - 6;
      const badgeY = blockTop - 1;
      doc.setDrawColor(sc[0], sc[1], sc[2]);
      doc.setLineWidth(0.4);
      doc.circle(badgeX, badgeY, 4.5, "S");
      doc.setFont(FONT, "bold");
      doc.setFontSize(7.5);
      doc.setTextColor(sc[0], sc[1], sc[2]);
      doc.text(`${displayScore}`, badgeX, badgeY + 1.2, { align: "center" });
      // Name the quantity, as the on-screen row does: a bare number on a printed page the
      // recruiter forwards to a hiring manager is otherwise unattributable.
      doc.setFont(FONT, "normal");
      doc.setFontSize(4.6);
      doc.text(BADGE_LABEL[sortBy], badgeX, badgeY + 6.6, { align: "center" });
    }

    // ── Name ─────────────────────────────────────────────
    doc.setFont(FONT, "bold");
    doc.setFontSize(LINE.name);
    setColor(COLOR.black);
    const nameText = dev.name || dev.login;
    const maxNameW = cw - 20; // leave room for score badge
    const truncName = doc.getTextWidth(nameText) > maxNameW
      ? nameText.slice(0, Math.floor(maxNameW / doc.getTextWidth("M"))) + "..."
      : nameText;
    doc.text(truncName, MARGIN.left, y);
    y += 5;

    // ── @login ───────────────────────────────────────────
    doc.setFont(FONT, "normal");
    doc.setFontSize(LINE.login);
    setColor(COLOR.mid);
    doc.text(`@${dev.login}`, MARGIN.left, y);
    y += RHYTHM + 1;

    // ── Location ─────────────────────────────────────────
    if (dev.location) {
      doc.setFont(FONT, "normal");
      doc.setFontSize(LINE.meta);
      setColor(COLOR.mid);
      doc.text(dev.location, MARGIN.left, y);
      y += RHYTHM;
    }

    // ── Languages ────────────────────────────────────────
    doc.setFont(FONT, "normal");
    doc.setFontSize(LINE.meta);
    setColor(COLOR.dark);
    doc.text(dev.topLanguages.slice(0, 6).join("  ·  "), MARGIN.left, y);
    y += RHYTHM + 2;

    // ── HR Summary ───────────────────────────────────────
    if (dev.hrSummary) {
      doc.setFont(FONT, "normal");
      doc.setFontSize(LINE.body);
      setColor(COLOR.dark);
      const lines = doc.splitTextToSize(dev.hrSummary, cw - 16);
      const displayLines = lines.slice(0, 3);
      doc.text(displayLines, MARGIN.left, y);
      y += displayLines.length * RHYTHM + 1;
    }

    // ── GitHub URL ───────────────────────────────────────
    doc.setFont(FONT, "normal");
    doc.setFontSize(LINE.url);
    setColor(COLOR.light);
    doc.text(dev.profileUrl, MARGIN.left, y);
    y += RHYTHM + 2;

    // ── Separator rule ───────────────────────────────────
    if (i < developers.length - 1) {
      doc.setDrawColor(COLOR.rule[0], COLOR.rule[1], COLOR.rule[2]);
      doc.setLineWidth(0.2);
      doc.line(MARGIN.left, y, pw - MARGIN.right, y);
      y += RHYTHM * 2;
    }
  });

  addFooter();
  doc.save(`${filename}.pdf`);
}
