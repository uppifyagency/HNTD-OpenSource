// The only reader of NEXT_PUBLIC_HNTD_MODE. "local" is set by scripts/local/setup.sh.
export type AppMode = "cloud" | "local";

export function parseAppMode(raw: string | undefined): AppMode {
  if (raw === undefined || raw === "" || raw === "cloud") return "cloud";
  if (raw === "local") return "local";
  throw new Error(`NEXT_PUBLIC_HNTD_MODE must be "cloud" or "local", got "${raw}"`);
}

// Spelled out in full so Next inlines it into client bundles.
export const APP_MODE: AppMode = parseAppMode(process.env.NEXT_PUBLIC_HNTD_MODE);
