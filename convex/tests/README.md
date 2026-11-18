# Convex Function Tests

## Strategy
- Unit tests for Convex functions require convex-test package
- Install: `npm install --save-dev convex-test`
- See: https://docs.convex.dev/testing

## Priority Tests Needed
1. Authorization: verify non-admin users cannot call admin mutations
2. Task creation: verify recruiterId is derived from auth context
3. Developer upsert: verify idempotency by githubId
4. getTask: verify ownership check (non-owner gets null)
