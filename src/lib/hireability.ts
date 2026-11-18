/**
 * Hireability signal — pure derivation of the company × hireable matrix.
 *
 * `hireable` is GitHub's SELF-DECLARED "Available for hire" flag (Convex `developers.hireable`,
 * sourced from GitHub `user.isHireable`). It is NOT an AI judgment — `false`/`null` means
 * "no declared signal", never "won't move". We therefore surface a positive badge only for the
 * two `*-open` quadrants and never render a negative one.
 *
 * Spec: artifacts/hireability-badge/SPEC.md
 */

export type HireabilityQuadrant =
  | "employed-open"
  | "independent-open"
  | "employed-undeclared"
  | "independent-undeclared";

export interface HireabilitySignal {
  /** Always set — the full company×hireable quadrant, for all four cases. */
  quadrant: HireabilityQuadrant;
  /** True only for the two `*-open` quadrants (self-declared available). */
  show: boolean;
  /** Badge label, empty when hidden. */
  label: string;
  /** Badge context line, empty when hidden. */
  context: string;
}

export function hireabilitySignal(
  hireable: boolean | null | undefined,
  company: string | null | undefined,
): HireabilitySignal {
  const trimmedCompany = (company ?? "").trim();
  const employed = trimmedCompany.length > 0;
  const open = hireable === true;

  if (open && employed) {
    return {
      quadrant: "employed-open",
      show: true,
      label: "Open to offers",
      context: `currently ${trimmedCompany}`,
    };
  }
  if (open && !employed) {
    return {
      quadrant: "independent-open",
      show: true,
      label: "Open to offers",
      context: "independent",
    };
  }
  return {
    quadrant: employed ? "employed-undeclared" : "independent-undeclared",
    show: false,
    label: "",
    context: "",
  };
}
