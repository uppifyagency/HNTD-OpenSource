const BACKEND_LANGS = new Set([
  "Java", "Python", "Go", "Rust", "C#", "PHP", "Ruby", "Scala", "Kotlin", "C++", "C",
]);
const FRONTEND_LANGS = new Set([
  "JavaScript", "TypeScript", "Vue", "Svelte", "CSS", "HTML", "SCSS",
]);
const DATA_LANGS = new Set([
  "Jupyter Notebook", "MATLAB", "Julia", "R",
]);
const DEVOPS_LANGS = new Set([
  "Shell", "Dockerfile", "Nix", "HCL",
]);
const MOBILE_LANGS = new Set([
  "Kotlin", "Dart", "Swift",
]);

export type PoolCategory = "backend" | "frontend" | "fullstack" | "data" | "devops" | "mobile";

export const CATEGORY_LABELS: Record<PoolCategory, string> = {
  backend: "Backend",
  frontend: "Frontend",
  fullstack: "Fullstack",
  data: "Data & AI",
  devops: "DevOps",
  mobile: "Mobile",
};

export function deriveCategories(topLanguages: string[]): PoolCategory[] {
  const cats: PoolCategory[] = [];
  const hasBackend = topLanguages.some((l) => BACKEND_LANGS.has(l));
  const hasFrontend = topLanguages.some((l) => FRONTEND_LANGS.has(l));

  if (hasBackend && hasFrontend) {
    cats.push("fullstack");
  } else {
    if (hasBackend) cats.push("backend");
    if (hasFrontend) cats.push("frontend");
  }
  if (topLanguages.some((l) => DATA_LANGS.has(l))) cats.push("data");
  if (topLanguages.some((l) => DEVOPS_LANGS.has(l))) cats.push("devops");
  if (topLanguages.some((l) => MOBILE_LANGS.has(l))) cats.push("mobile");

  return cats.length > 0 ? cats : ["backend"];
}

export function scoreToStars(score: number | undefined): number {
  if (score === undefined) return 0;
  if (score >= 70) return 5;
  if (score >= 55) return 4;
  if (score >= 40) return 3;
  if (score >= 25) return 2;
  return 1;
}
