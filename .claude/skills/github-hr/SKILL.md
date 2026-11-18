---
name: github-hr
description: >
  GitHub HR talent pipeline. Process recruiter tasks: search GitHub developers,
  score repositories with AI, push results to Convex.
  Triggers on: "github-hr", "run tasks", "score developers", "find developers",
  "process tasks".
user_invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - WebFetch
  - Agent
---

# GitHub HR — Slash Command Entry Point

When this skill is invoked, load and follow the master orchestrator at:

```
skill/github-hr/SKILL.md
```

Read that file and execute the appropriate command based on the arguments passed.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/github-hr help` | Show all commands with descriptions |
| `/github-hr run --task <TASK_ID>` | Process a single task (recommended) |
| `/github-hr run` | Process ALL pending tasks |
| `/github-hr run --priority-only` | Process priority tasks only |
| `/github-hr jd-parse <TASK_ID>` | Parse JD into structured profile |
| `/github-hr fetch <TASK_ID>` | Search & fetch developers only |
| `/github-hr score <TASK_ID>` | Score fetched developers only |
| `/github-hr push <TASK_ID>` | Push scored results to Convex |
| `/github-hr jobs` | Show all users + tasks (like /context) |
| `/github-hr status` | Check pending task queue |
| `/github-hr users` | List users with plan, email, task count |
| `/github-hr tasks <USER>` | Show tasks for a user (by name or ID) |
| `/github-hr reset <TASK_ID>` | Reset task to "pending" for re-processing |
| `/github-hr delete <TASK_ID>` | Delete task + results (irreversible) |
| `/github-hr results <TASK_ID>` | Show developer leaderboard for a task |
| `/github-hr create <USER_ID>` | Create a task from CLI (for testing) |
