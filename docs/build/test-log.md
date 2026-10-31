# Build Test Log

One row per test or exit check. Gate tasks record `II ✔` and `VI ✔` in the Constitution column.

| Date | Phase/Task | Test | Result | Constitution | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2026-10-31 | T007 | Staged file with a fake `ghp_` token is blocked by gitleaks (`pre-commit run gitleaks`) | PASS | VI ✔ | RuleID `github-pat`, exit 1. File unstaged and deleted afterwards |
