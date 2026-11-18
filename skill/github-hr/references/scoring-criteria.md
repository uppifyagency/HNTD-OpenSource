# Developer Scoring Criteria

Score each developer from 0-100 based on their top 3 repositories.

## Evaluation Rubric

### Code Quality (20 points)
- 0-5: Inconsistent formatting, no structure, copy-paste code
- 6-10: Basic structure, some formatting, functional but messy
- 11-15: Clean code, consistent style, reasonable abstractions
- 16-20: Excellent readability, solid patterns, professional quality

### Architecture & Structure (20 points)
- 0-5: No project structure, everything in one file
- 6-10: Basic file separation, some organization
- 11-15: Clear separation of concerns, good folder structure
- 16-20: Well-architected, modular, scalable patterns

### Testing (15 points)
- 0-3: No tests
- 4-7: Some tests present but poor coverage
- 8-11: Good test coverage, meaningful assertions
- 12-15: Comprehensive tests, edge cases covered, CI integration

### Documentation (15 points)
- 0-3: No README or documentation
- 4-7: Basic README with setup instructions
- 8-11: Good README, API docs, clear explanations
- 12-15: Excellent docs, examples, contribution guide, well-commented where needed

### Project Complexity & Ambition (15 points)
- 0-3: Trivial projects (hello world, tutorials)
- 4-7: Small utilities, simple CRUD apps
- 8-11: Medium complexity, real-world use cases
- 12-15: Complex systems, libraries used by others, innovative solutions

### Consistency & Activity (15 points)
- 0-3: Sporadic commits, abandoned projects
- 4-7: Semi-regular activity, some maintenance
- 8-11: Regular commits, clear commit messages, active maintenance
- 12-15: Very active, clean git history, responsive to issues/PRs

## Output Format

For each developer, produce a JSON object with individual category scores in `scoreBreakdown` and a total `score` (sum of all categories):

```json
{
  "login": "developer-username",
  "score": 72,
  "scoreBreakdown": {
    "codeQuality": 15,
    "architecture": 16,
    "testing": 10,
    "documentation": 12,
    "complexity": 11,
    "consistency": 8
  },
  "scoreComment": "Solid Laravel developer with clean architecture in 3 production-quality projects. Strong testing practices and well-documented APIs. Active contributor with consistent commit history.",
  "scoreModel": "claude-opus-4-6",
  "topRepo": "laravel-api-starter"
}
```

## Important Notes

- Score ONLY based on what you can see in repository code. Do not infer dimension scores from profile text. Bio is used only for must-have detection gates.
- A developer with 2 excellent repos scores higher than one with 10 mediocre ones.
- Weight recent activity more than old repos.
- Ignore forked repos unless the developer has made significant modifications.
- Ignore auto-generated code (scaffolding, boilerplate from frameworks).
