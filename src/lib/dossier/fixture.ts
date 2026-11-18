import type { Doc } from "../../../convex/_generated/dataModel";

/**
 * Shared dossier fixture — a realistic `developers` doc (+ a task with a JD rubric).
 * Used by the adapter unit test AND the /editorial/candidate preview page, so the
 * de-faked editorial dossier renders from the SAME shape the adapter produces in prod.
 */
export const SAMPLE_NOW = Date.UTC(2026, 4, 2, 14, 22, 0); // 2026-05-02 14:22 UTC

export const sampleDeveloper = {
  _id: "dev_marina" as Doc<"developers">["_id"],
  _creationTime: 0,
  githubId: "123456",
  login: "marina-rossi",
  name: "Marina Rossi",
  email: "marina@example.dev",
  location: "milano, IT",
  company: "Tinybird",
  hireable: true,
  followers: 3412,
  publicRepos: 12,
  profileUrl: "https://github.com/marina-rossi",
  avatarUrl: "https://avatars.githubusercontent.com/u/583231?v=4",
  topLanguages: ["Go", "Rust", "Shell", "TypeScript"],
  lastPushAt: SAMPLE_NOW - 86400000, // 1 day before SAMPLE_NOW
  topRepos: [
    { name: "tinybird/cli", url: "https://github.com/tinybird/cli", stars: 3412, forks: 210, language: "Go", description: "Command-line client for Tinybird.", topics: ["cli", "go", "devtools"] },
    { name: "prometheus/client_golang", url: "https://github.com/prometheus/client_golang", stars: 5187, forks: 1200, language: "Go", description: "Prometheus instrumentation library for Go applications.", topics: ["go", "metrics"] },
    { name: "marina-rossi/k-event-bus", url: "https://github.com/marina-rossi/k-event-bus", stars: 892, forks: 41, language: "Rust", description: "A small, fast event bus.", topics: ["rust", "events"] },
    { name: "go-kit/kit", url: "https://github.com/go-kit/kit", stars: 26100, forks: 2400, language: "Go", description: "A standard library for microservices.", topics: ["go", "microservices"] },
  ],
  scoreComment: "Maintainer-grade backend engineer with clean, modular Go and consistent contribution cadence across high-traffic open-source projects.",
  scoreBreakdown: { codeQuality: 19, architecture: 19, testing: 14, documentation: 13, complexity: 15, consistency: 14 },
  matchConfidence: 94,
  matchReason: "Deep Go + infra match against the JD's backend depth requirement.",
  objectiveScore: 94,
  jdScoreBreakdown: { backend_depth: 38, go_expertise: 28, infra: 20 },
  jdAssessment: "Strong fit for the senior backend role: ownership of a 3.4k-star CLI, Prometheus contributions, and consistent test discipline.",
  indexedAt: SAMPLE_NOW,
  updatedAt: SAMPLE_NOW,
  totalCommitContributions: 1847,
  totalPullRequestContributions: 96,
  totalPullRequestReviewContributions: 187,
  contributionDays: 312,
  isGitHubStar: true,
  isDeveloperProgramMember: false,
  hasSponsorsListing: true,
  deterministicRank: 1,
  languageFitScore: 91,
  collaborationScore: 78,
  projectMaturityScore: 84,
  pinnedRepos: [{ name: "k-event-bus", primaryLanguage: "Rust", stars: 892, description: "A small, fast event bus." }],
} as unknown as Doc<"developers">;

export const sampleTask = {
  _id: "task_1" as Doc<"tasks">["_id"],
  _creationTime: 0,
  jdProfile: {
    scoringRubric: {
      dimensions: [
        { name: "backend_depth", weight: 40, description: "", signals: [] },
        { name: "go_expertise", weight: 30, description: "", signals: [] },
        { name: "infra", weight: 30, description: "", signals: [] },
      ],
      mustHave: [],
      niceToHave: [],
      dealBreakers: [],
    },
    version: 1,
  },
} as unknown as Doc<"tasks">;
