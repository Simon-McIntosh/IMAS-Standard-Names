## Summary

<!-- Briefly describe what this PR adds or changes. -->

## Evidence for new vocabulary tokens

<!--
  Every PR that adds or modifies vocabulary tokens MUST complete this section.
  A token is justified when it appears in ≥ 3 distinct IMAS DD paths or
  facility signals.  The imas-codex `sn gaps` command can provide this data.

  Delete this section if the PR does not touch vocabulary files.
-->

- **Token(s) proposed:** <!-- e.g. runaway_electron, curvature_drift -->
- **Number of distinct DD paths demanding this token (N):** <!-- must be ≥ 3 -->
- **Paths (list at least 3):**
  - <!-- path 1 -->
  - <!-- path 2 -->
  - <!-- path 3 -->
- **Why an existing token does not suffice:**
  <!-- One paragraph explaining semantic gap -->

## Motivation

<!-- Why is this change needed? Link to an imas-codex issue or VocabGap report if applicable. -->

## Changes

<!-- List the files changed and what was modified. -->

## Testing

- [ ] All existing tests pass (`uv run pytest`)
- [ ] New tests added for any new grammar rules or validation logic
- [ ] Grammar validates correctly (`uv run pytest tests/`)

## Checklist

- [ ] I have read the [CONTRIBUTING.md](../CONTRIBUTING.md) guidelines
- [ ] Conventional commit message format used
- [ ] For vocabulary additions: N ≥ 3 evidence provided above
