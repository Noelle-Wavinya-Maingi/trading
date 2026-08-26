## Summary

<!-- What does this PR change, and why. A sentence or two is enough. -->

## Test plan

<!-- How was this verified: which suites, which throwaway database(s),
     any manual/live-DB check performed. -->

## Checklist

- [ ] If this changes a field's type/name or renames a module: matching
      `migrations/` script present, version bumped (see `docs/MIGRATIONS.md`).
- [ ] If this is a behavior-changing PR: a test exists that is proven to
      have failed on the pre-fix code (not just added and passing now) —
      see `docs/TESTING.md`.
- [ ] If this touches a compute method or a workflow state transition: I
      reproduced the bug/scenario live against a real database, not just in
      the test suite.
