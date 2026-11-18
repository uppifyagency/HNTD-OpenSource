/**
 * GitHub Linguist language mapping for recruiter search terms.
 *
 * Drives the SmartTagInput: classifies user input as language (green chip)
 * or keyword (blue chip), and suggests related languages.
 *
 * Source: docs/research/github-language-classification-and-search.md
 */

export type TermClassification = "language" | "keyword" | "both";

export interface LanguageMapEntry {
  /** Display name */
  label: string;
  /** Exact Linguist language name, or null if not a language */
  linguistName: string | null;
  /** language: values for GitHub user search */
  searchLanguages: string[];
  /** Keyword values to use in search */
  searchKeywords: string[];
  /** Strategy type */
  strategy: TermClassification;
  /** Category for autocomplete grouping */
  category: string;
}

export const GITHUB_LANGUAGE_MAP: Record<string, LanguageMapEntry> = {
  // --- Actual programming languages ---
  python: {
    label: "Python",
    linguistName: "Python",
    searchLanguages: ["python"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  javascript: {
    label: "JavaScript",
    linguistName: "JavaScript",
    searchLanguages: ["javascript"],
    searchKeywords: [],
    strategy: "language",
    category: "Frontend",
  },
  typescript: {
    label: "TypeScript",
    linguistName: "TypeScript",
    searchLanguages: ["typescript"],
    searchKeywords: [],
    strategy: "language",
    category: "Frontend",
  },
  java: {
    label: "Java",
    linguistName: "Java",
    searchLanguages: ["java"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  go: {
    label: "Go",
    linguistName: "Go",
    searchLanguages: ["go"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  ruby: {
    label: "Ruby",
    linguistName: "Ruby",
    searchLanguages: ["ruby"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  rust: {
    label: "Rust",
    linguistName: "Rust",
    searchLanguages: ["rust"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  "c#": {
    label: "C#",
    linguistName: "C#",
    searchLanguages: ["c#"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  csharp: {
    label: "C#",
    linguistName: "C#",
    searchLanguages: ["c#"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  php: {
    label: "PHP",
    linguistName: "PHP",
    searchLanguages: ["php"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  scala: {
    label: "Scala",
    linguistName: "Scala",
    searchLanguages: ["scala"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  kotlin: {
    label: "Kotlin",
    linguistName: "Kotlin",
    searchLanguages: ["kotlin"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  swift: {
    label: "Swift",
    linguistName: "Swift",
    searchLanguages: ["swift"],
    searchKeywords: [],
    strategy: "language",
    category: "Mobile",
  },
  dart: {
    label: "Dart",
    linguistName: "Dart",
    searchLanguages: ["dart"],
    searchKeywords: [],
    strategy: "language",
    category: "Mobile",
  },
  "c++": {
    label: "C++",
    linguistName: "C++",
    searchLanguages: ["c++"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  c: {
    label: "C",
    linguistName: "C",
    searchLanguages: ["c"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  elixir: {
    label: "Elixir",
    linguistName: "Elixir",
    searchLanguages: ["elixir"],
    searchKeywords: [],
    strategy: "language",
    category: "Backend",
  },
  r: {
    label: "R",
    linguistName: "R",
    searchLanguages: ["r"],
    searchKeywords: [],
    strategy: "language",
    category: "Data",
  },
  shell: {
    label: "Shell",
    linguistName: "Shell",
    searchLanguages: ["shell"],
    searchKeywords: [],
    strategy: "language",
    category: "DevOps",
  },
  vue: {
    label: "Vue",
    linguistName: "Vue",
    searchLanguages: ["vue"],
    searchKeywords: [],
    strategy: "language",
    category: "Frontend",
  },

  // --- Frameworks / Tools (not GitHub languages) ---
  docker: {
    label: "Docker",
    linguistName: null,
    searchLanguages: ["dockerfile"],
    searchKeywords: ["docker", "container"],
    strategy: "both",
    category: "DevOps",
  },
  dockerfile: {
    label: "Dockerfile",
    linguistName: "Dockerfile",
    searchLanguages: ["dockerfile"],
    searchKeywords: ["docker"],
    strategy: "language",
    category: "DevOps",
  },
  kubernetes: {
    label: "Kubernetes",
    linguistName: null,
    searchLanguages: ["go", "shell"],
    searchKeywords: ["kubernetes", "k8s"],
    strategy: "keyword",
    category: "DevOps",
  },
  k8s: {
    label: "Kubernetes",
    linguistName: null,
    searchLanguages: ["go", "shell"],
    searchKeywords: ["kubernetes", "k8s"],
    strategy: "keyword",
    category: "DevOps",
  },
  terraform: {
    label: "Terraform",
    linguistName: "HCL",
    searchLanguages: ["hcl"],
    searchKeywords: ["terraform"],
    strategy: "both",
    category: "DevOps",
  },
  ansible: {
    label: "Ansible",
    linguistName: null,
    searchLanguages: ["python", "shell"],
    searchKeywords: ["ansible"],
    strategy: "keyword",
    category: "DevOps",
  },
  react: {
    label: "React",
    linguistName: null,
    searchLanguages: ["javascript", "typescript"],
    searchKeywords: ["react"],
    strategy: "both",
    category: "Frontend",
  },
  "react native": {
    label: "React Native",
    linguistName: null,
    searchLanguages: ["javascript", "typescript"],
    searchKeywords: ["react-native"],
    strategy: "keyword",
    category: "Mobile",
  },
  angular: {
    label: "Angular",
    linguistName: null,
    searchLanguages: ["typescript"],
    searchKeywords: ["angular"],
    strategy: "both",
    category: "Frontend",
  },
  "vue.js": {
    label: "Vue.js",
    linguistName: "Vue",
    searchLanguages: ["vue", "javascript", "typescript"],
    searchKeywords: ["vue", "vuejs"],
    strategy: "both",
    category: "Frontend",
  },
  "node.js": {
    label: "Node.js",
    linguistName: null,
    searchLanguages: ["javascript", "typescript"],
    searchKeywords: ["nodejs", "node"],
    strategy: "both",
    category: "Backend",
  },
  node: {
    label: "Node.js",
    linguistName: null,
    searchLanguages: ["javascript", "typescript"],
    searchKeywords: ["nodejs"],
    strategy: "both",
    category: "Backend",
  },
  nodejs: {
    label: "Node.js",
    linguistName: null,
    searchLanguages: ["javascript", "typescript"],
    searchKeywords: ["nodejs"],
    strategy: "both",
    category: "Backend",
  },
  "spring boot": {
    label: "Spring Boot",
    linguistName: null,
    searchLanguages: ["java", "kotlin"],
    searchKeywords: ["spring", "spring-boot"],
    strategy: "both",
    category: "Backend",
  },
  spring: {
    label: "Spring",
    linguistName: null,
    searchLanguages: ["java", "kotlin"],
    searchKeywords: ["spring"],
    strategy: "both",
    category: "Backend",
  },
  django: {
    label: "Django",
    linguistName: null,
    searchLanguages: ["python"],
    searchKeywords: ["django"],
    strategy: "both",
    category: "Backend",
  },
  flask: {
    label: "Flask",
    linguistName: null,
    searchLanguages: ["python"],
    searchKeywords: ["flask"],
    strategy: "both",
    category: "Backend",
  },
  ".net": {
    label: ".NET",
    linguistName: null,
    searchLanguages: ["c#"],
    searchKeywords: ["dotnet", ".net", "asp.net"],
    strategy: "both",
    category: "Backend",
  },
  dotnet: {
    label: ".NET",
    linguistName: null,
    searchLanguages: ["c#"],
    searchKeywords: ["dotnet", ".net"],
    strategy: "both",
    category: "Backend",
  },
  ios: {
    label: "iOS",
    linguistName: null,
    searchLanguages: ["swift", "objective-c"],
    searchKeywords: ["ios"],
    strategy: "both",
    category: "Mobile",
  },
  android: {
    label: "Android",
    linguistName: null,
    searchLanguages: ["kotlin", "java"],
    searchKeywords: ["android"],
    strategy: "both",
    category: "Mobile",
  },
  "machine learning": {
    label: "Machine Learning",
    linguistName: null,
    searchLanguages: ["python", "jupyter-notebook"],
    searchKeywords: ["machine-learning", "deep-learning"],
    strategy: "keyword",
    category: "Data",
  },
  ml: {
    label: "Machine Learning",
    linguistName: null,
    searchLanguages: ["python", "jupyter-notebook"],
    searchKeywords: ["machine-learning", "ml"],
    strategy: "keyword",
    category: "Data",
  },
  ai: {
    label: "AI",
    linguistName: null,
    searchLanguages: ["python", "jupyter-notebook"],
    searchKeywords: ["artificial-intelligence", "ai", "machine-learning"],
    strategy: "keyword",
    category: "Data",
  },
  "data science": {
    label: "Data Science",
    linguistName: null,
    searchLanguages: ["python", "r", "jupyter-notebook"],
    searchKeywords: ["data-science"],
    strategy: "keyword",
    category: "Data",
  },
  aws: {
    label: "AWS",
    linguistName: null,
    searchLanguages: ["python", "hcl"],
    searchKeywords: ["aws", "amazon-web-services"],
    strategy: "keyword",
    category: "DevOps",
  },
  devops: {
    label: "DevOps",
    linguistName: null,
    searchLanguages: ["dockerfile", "hcl", "shell"],
    searchKeywords: ["devops"],
    strategy: "keyword",
    category: "DevOps",
  },
  flutter: {
    label: "Flutter",
    linguistName: null,
    searchLanguages: ["dart"],
    searchKeywords: ["flutter"],
    strategy: "both",
    category: "Mobile",
  },
};

/** Split raw input on common separators */
export function splitInput(raw: string): string[] {
  return raw
    .split(/\s+and\s+|,|;|\+/i)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

/** Classify a single term using the map */
export function classifyTerm(term: string): {
  entry: LanguageMapEntry | null;
  isLanguage: boolean;
} {
  const key = term.toLowerCase().trim();
  const entry = GITHUB_LANGUAGE_MAP[key] ?? null;
  return {
    entry,
    isLanguage: entry?.linguistName != null,
  };
}

/** Get unique suggested languages for a list of classified terms */
export function getSuggestions(
  terms: Array<{ term: string; entry: LanguageMapEntry | null }>
): string[] {
  const currentLanguages = new Set(
    terms
      .filter((t) => t.entry?.linguistName)
      .map((t) => t.entry!.linguistName!.toLowerCase())
  );

  const suggestions = new Set<string>();
  for (const { entry } of terms) {
    if (!entry) continue;
    for (const lang of entry.searchLanguages) {
      const mapEntry = GITHUB_LANGUAGE_MAP[lang.toLowerCase()];
      const label = mapEntry?.label ?? lang;
      if (!currentLanguages.has(lang.toLowerCase())) {
        suggestions.add(label);
      }
    }
  }
  return Array.from(suggestions);
}
