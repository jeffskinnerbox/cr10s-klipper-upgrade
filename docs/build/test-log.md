# Build Test Log

One row per test or exit check. Gate tasks record `II ✔` and `VI ✔` in the Constitution column.

| Date | Phase/Task | Test | Result | Constitution | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2026-10-31 | T007 | Staged file with a fake `ghp_` token is blocked by gitleaks (`pre-commit run gitleaks`) | PASS | VI ✔ | RuleID `github-pat`, exit 1. File unstaged and deleted afterwards |
| 2026-10-31 | T023 / Plan Phase 0 exit | `make check`: ruff, shellcheck, markdownlint (fix off), 159 unit + integration tests | PASS | IV ✔ VI ✔ | 2 live tests deselected (need `--live`). gitleaks passed on the T009-T022 commit |
| 2026-10-31 | T025 | Pad on Wi-Fi at 192.168.1.152. `/server/info`, `/printer/info`, `/printer/objects/query` answer on 7125. `cr10s-status` runs with config `pad.url` | PASS | II ✔ | Klipper `shutdown` (no MCU) is expected. IP reservation deferred |
| 2026-10-31 | T026 | R8 on the Pad: wrong checksum, good upload (`print=false`), metadata | PASS | II ✔ | Wrong checksum is HTTP 500 (not 422), reply unwrapped; client fixed, 160 tests pass. Test files deleted |
| 2026-10-31 | T027 / Plan Phase 1 exit | `make test-live` against the Pad (192.168.1.152:7125): `/server/info` and `print_stats` | PASS | II ✔ VI ✔ | 2 live tests passed. Klipper `shutdown` (no MCU) is expected. Nothing printed or stored |
