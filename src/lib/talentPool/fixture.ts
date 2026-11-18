import type { PoolDev } from "./talentPoolViewModel";

/** Sample pool for the /editorial/talent preview (no auth) and talentPoolVM tests. */
const d = (o: Record<string, unknown>) => o as unknown as PoolDev;

/** Mix of full + blurred profiles, multiple categories, varied scores/signals. */
export const samplePool: PoolDev[] = [
  d({ _id: "p1", login: "topdev1", name: "Elim Garak", location: "Cardassia", topLanguages: ["Go", "Rust"], objectiveScore: 91, followers: 4200, publicRepos: 64, hrSummary: "Maintainer-grade Go infra; clean modular boundaries, heavy test coverage.", profileUrl: "https://github.com/topdev1", topRepos: [{ name: "topdev1/tailor", url: "#", stars: 8100 }, { name: "topdev1/obsidian", url: "#", stars: 1200 }] }),
  d({ _id: "p2", login: "topdev2", name: "Jean Luc", location: "Paris, FR", topLanguages: ["Python", "Django"], objectiveScore: 84, followers: 1800, publicRepos: 52, hrSummary: "Senior Python; strong async + data pipelines, pragmatic reviewer.", profileUrl: "https://github.com/topdev2", topRepos: [{ name: "topdev2/warp", url: "#", stars: 640 }] }),
  d({ _id: "p3", login: "topdev3", name: "Laura Lloc", location: "Barcelona, ES", topLanguages: ["TypeScript", "React", "Node"], objectiveScore: 78, followers: 920, publicRepos: 88, hrSummary: "Fullstack TS; design-system ownership, accessibility-minded.", profileUrl: "https://github.com/topdev3", topRepos: [{ name: "topdev3/atlas", url: "#", stars: 410 }] }),
  d({ _id: "p4", login: "dev-9f2a1c", location: "Berlin, DE", topLanguages: ["Kotlin", "Swift"], objectiveScore: 72, followers: 310, publicRepos: 24, blurred: true }),
  d({ _id: "p5", login: "dev-44b7e0", location: "Remote", topLanguages: ["Python", "Pandas", "PyTorch"], objectiveScore: 66, followers: 140, publicRepos: 19, blurred: true }),
  d({ _id: "p6", login: "okonkwo", name: "Chinua Okonkwo", location: "Lagos, NG", topLanguages: ["Go", "Terraform", "Kubernetes"], objectiveScore: 81, followers: 530, publicRepos: 41, hrSummary: "DevOps-leaning backend; IaC + platform reliability.", profileUrl: "https://github.com/okonkwo", topRepos: [{ name: "okonkwo/helmsman", url: "#", stars: 980 }] }),
];
