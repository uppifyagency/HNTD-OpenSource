export interface VisibilityField {
  id: string;
  label: string;
}

export interface VisibilitySection {
  id: string;
  label: string;
  fields: VisibilityField[];
}

export interface VisibilityPage {
  id: string;
  label: string;
  sections: VisibilitySection[];
}

export const visibilityRegistry: VisibilityPage[] = [
  {
    id: "landing",
    label: "Landing Page",
    sections: [
      { id: "landing.navbar", label: "Navigation Bar", fields: [] },
      { id: "landing.hero", label: "Hero Section", fields: [] },
      { id: "landing.problemCards", label: "Problem Cards", fields: [] },
      { id: "landing.searchDemo", label: "Search Demo", fields: [] },
      { id: "landing.howItWorks", label: "How It Works", fields: [] },
      { id: "landing.whyGithubHr", label: "Why GitHub HR", fields: [] },
      { id: "landing.outreachComparison", label: "Outreach Comparison", fields: [] },
      { id: "landing.devGrid", label: "Developer Grid", fields: [] },
      { id: "landing.pricing", label: "Pricing", fields: [] },
      { id: "landing.faq", label: "FAQ", fields: [] },
      { id: "landing.comparison", label: "Competitor Comparison", fields: [] },
      { id: "landing.talentMapForm", label: "Talent Map Form", fields: [] },
      { id: "landing.cta", label: "Call-to-Action", fields: [] },
      { id: "landing.footer", label: "Footer", fields: [] },
    ],
  },
  {
    id: "dashboard",
    label: "Dashboard",
    sections: [
      { id: "dashboard.welcomeBanner", label: "Welcome Banner", fields: [] },
      {
        id: "dashboard.stats",
        label: "Statistics",
        fields: [
          { id: "dashboard.stats.totalTasks", label: "Active Tasks" },
          { id: "dashboard.stats.completed", label: "Completed" },
          { id: "dashboard.stats.developersFound", label: "Developers Found" },
        ],
      },
      {
        id: "dashboard.recentTasks",
        label: "Recent Tasks",
        fields: [
          { id: "dashboard.recentTasks.statusBadge", label: "Status Badge" },
          { id: "dashboard.recentTasks.modeBadge", label: "Mode Badge" },
          { id: "dashboard.recentTasks.resultCount", label: "Result Count" },
          { id: "dashboard.recentTasks.date", label: "Creation Date" },
        ],
      },
    ],
  },
  {
    id: "newTask",
    label: "New Task",
    sections: [
      {
        id: "newTask.manualMode",
        label: "Quick Search (Manual Mode)",
        fields: [
          { id: "newTask.manualMode.searchTerms", label: "Search Terms" },
          { id: "newTask.manualMode.country", label: "Country" },
          { id: "newTask.manualMode.city", label: "City / Region" },
          { id: "newTask.manualMode.minActivity", label: "Min Activity" },
        ],
      },
      {
        id: "newTask.jdMode",
        label: "Job Description Mode",
        fields: [
          { id: "newTask.jdMode.jobDescription", label: "Job Description" },
        ],
      },
      { id: "newTask.maxResults", label: "Max Results", fields: [] },
    ],
  },
  {
    id: "taskResults",
    label: "Task Results",
    sections: [
      { id: "taskResults.taskHeader", label: "Task Header", fields: [] },
      {
        id: "taskResults.jdProfile",
        label: "JD Profile Panel",
        fields: [
          { id: "taskResults.jdProfile.languages", label: "Languages" },
          { id: "taskResults.jdProfile.location", label: "Location" },
          { id: "taskResults.jdProfile.role", label: "Role" },
          { id: "taskResults.jdProfile.keywords", label: "Keywords" },
          { id: "taskResults.jdProfile.scoringRubric", label: "Scoring Rubric" },
          { id: "taskResults.jdProfile.mustHaves", label: "Must-Haves" },
        ],
      },
      { id: "taskResults.extractedParamsNotice", label: "Notice parametri estratti", fields: [] },
      { id: "taskResults.sortControls", label: "Sort Controls", fields: [] },
      { id: "taskResults.passResults", label: "Pass Results Summary", fields: [] },
      {
        id: "taskResults.devCards",
        label: "Developer Cards",
        fields: [
          { id: "taskResults.devCards.avatar", label: "Avatar" },
          { id: "taskResults.devCards.score", label: "Score Badge" },
          { id: "taskResults.devCards.matchConfidence", label: "Match Confidence" },
          { id: "taskResults.devCards.languages", label: "Languages" },
          { id: "taskResults.devCards.jdScoreBreakdown", label: "JD Score Breakdown" },
          { id: "taskResults.devCards.scoreBreakdown", label: "Score Breakdown" },
          { id: "taskResults.devCards.activity", label: "GitHub Activity" },
        ],
      },
    ],
  },
  {
    id: "devProfile",
    label: "Developer Profile",
    sections: [
      {
        id: "devProfile.header",
        label: "Header",
        fields: [
          { id: "devProfile.header.objectiveScore", label: "Objective Score" },
          { id: "devProfile.header.matchConfidence", label: "Match Confidence" },
          { id: "devProfile.header.location", label: "Location" },
          { id: "devProfile.header.company", label: "Company" },
          { id: "devProfile.header.hireable", label: "Hireability" },
        ],
      },
      { id: "devProfile.bio", label: "Bio", fields: [] },
      {
        id: "devProfile.aiAssessment",
        label: "AI Assessment",
        fields: [
          { id: "devProfile.aiAssessment.scoreModel", label: "Score Model" },
        ],
      },
      { id: "devProfile.jdMatchAnalysis", label: "JD Match Analysis", fields: [] },
      { id: "devProfile.jdFitAssessment", label: "JD Fit Assessment", fields: [] },
      { id: "devProfile.jdScoreBreakdown", label: "JD Score Breakdown", fields: [] },
      {
        id: "devProfile.scoreBreakdown",
        label: "Score Breakdown",
        fields: [
          { id: "devProfile.scoreBreakdown.codeQuality", label: "Code Quality" },
          { id: "devProfile.scoreBreakdown.architecture", label: "Architecture" },
          { id: "devProfile.scoreBreakdown.testing", label: "Testing" },
          { id: "devProfile.scoreBreakdown.documentation", label: "Documentation" },
          { id: "devProfile.scoreBreakdown.complexity", label: "Complexity" },
          { id: "devProfile.scoreBreakdown.consistency", label: "Consistency" },
        ],
      },
      {
        id: "devProfile.githubActivity",
        label: "GitHub Activity",
        fields: [
          { id: "devProfile.githubActivity.commits", label: "Commits" },
          { id: "devProfile.githubActivity.prs", label: "PRs Opened" },
          { id: "devProfile.githubActivity.reviews", label: "Code Reviews" },
          { id: "devProfile.githubActivity.activeDays", label: "Active Days" },
        ],
      },
      { id: "devProfile.organizations", label: "Organizations", fields: [] },
      { id: "devProfile.externalContributions", label: "External Contributions", fields: [] },
      { id: "devProfile.badges", label: "Badges", fields: [] },
      { id: "devProfile.socialAccounts", label: "Social Accounts", fields: [] },
      { id: "devProfile.rankingBreakdown", label: "Ranking Breakdown", fields: [] },
      { id: "devProfile.pinnedRepos", label: "Pinned Repositories", fields: [] },
      { id: "devProfile.contact", label: "Contact", fields: [] },
      { id: "devProfile.languages", label: "Languages", fields: [] },
      { id: "devProfile.topRepos", label: "Top Repositories", fields: [] },
    ],
  },
  {
    id: "talentPool",
    label: "Talent Pool",
    sections: [
      { id: "talentPool.search", label: "Natural Language Search", fields: [] },
      { id: "talentPool.categoryFilters", label: "Category Filters", fields: [] },
      {
        id: "talentPool.devCard",
        label: "Developer Card",
        fields: [
          { id: "talentPool.devCard.avatar", label: "Avatar" },
          { id: "talentPool.devCard.name", label: "Name" },
          { id: "talentPool.devCard.location", label: "Location" },
          { id: "talentPool.devCard.starRating", label: "Star Rating" },
          { id: "talentPool.devCard.favoriteButton", label: "Favorite Button" },
          { id: "talentPool.devCard.searchSnippet", label: "Search Snippet" },
          { id: "talentPool.devCard.hrSummary", label: "HR Summary" },
          { id: "talentPool.devCard.languages", label: "Languages" },
          { id: "talentPool.devCard.bio", label: "Bio" },
          { id: "talentPool.devCard.topRepos", label: "Top Repositories" },
          { id: "talentPool.devCard.githubLink", label: "GitHub Link" },
        ],
      },
    ],
  },
  {
    id: "pipeline",
    label: "Pipeline",
    sections: [
      { id: "pipeline.exportButtons", label: "Export Buttons", fields: [] },
      {
        id: "pipeline.kanbanCard",
        label: "Kanban Card",
        fields: [
          { id: "pipeline.kanbanCard.avatar", label: "Avatar" },
          { id: "pipeline.kanbanCard.score", label: "Score Badge" },
          { id: "pipeline.kanbanCard.hrSummary", label: "HR Summary" },
          { id: "pipeline.kanbanCard.languages", label: "Languages" },
          { id: "pipeline.kanbanCard.note", label: "Notes" },
        ],
      },
    ],
  },
  {
    id: "monitoring",
    label: "Monitoring",
    sections: [
      { id: "monitoring.statsRow1", label: "Stats Row 1", fields: [] },
      { id: "monitoring.statsRow2", label: "Stats Row 2", fields: [] },
      { id: "monitoring.activeTasks", label: "Active Tasks", fields: [] },
      { id: "monitoring.recentCompleted", label: "Recent Completed", fields: [] },
      { id: "monitoring.recentErrors", label: "Recent Errors", fields: [] },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    sections: [
      { id: "settings.accountInfo", label: "Account Info", fields: [] },
      {
        id: "settings.subscription",
        label: "Subscription",
        fields: [
          { id: "settings.subscription.currentPlan", label: "Current Plan" },
          { id: "settings.subscription.statusBadge", label: "Status Badge" },
          { id: "settings.subscription.planLimits", label: "Plan Limits" },
        ],
      },
    ],
  },
];

// Helper: get all field IDs for a section (for master toggle)
export function getSectionChildIds(sectionId: string): string[] {
  for (const page of visibilityRegistry) {
    for (const section of page.sections) {
      if (section.id === sectionId) {
        return section.fields.map((f) => f.id);
      }
    }
  }
  return [];
}
