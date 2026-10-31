# Moonraker Subset Contract

These are the only Moonraker endpoints the tools call. The fake server in
`tests/integration/conftest.py` serves exactly this set. Sources: [S22], [S23], [S45] in
[../plan.md](../plan.md#sources).

| Method | Path                                    | Used by        | Fake server behavior                              |
| :----- | :-------------------------------------- | :------------- | :------------------------------------------------ |
| GET    | `/server/info`                          | status, live   | `{"result":{"klippy_state":"ready",…}}`           |
| GET    | `/printer/objects/query?webhooks&print_stats&virtual_sdcard&extruder&heater_bed` | status, watch | Plays back scripted state snapshots |
| POST   | `/server/files/upload`                  | upload         | 201 + `{"result":{"item":{"path":…},"print_started":false,…}}` on a good checksum; 422 on a bad one; records the form fields |
| GET    | `/server/files/metadata?filename=…`     | upload         | `estimated_time`, `filament_total`                |
| DELETE | `/server/files/gcodes/<path>`           | live tests     | 200                                               |
| GET    | `/server/files/list?root=config`        | backup         | list of config files                              |
| GET    | `/server/files/config/<file>`           | backup         | file bytes                                        |

Rules checked by tests:

- The upload form MUST contain `print=false`, and `print=true` must never appear (asserted on every
  upload test).
- No tool may call `/printer/print/start`. The fake server fails the test if it is hit.
- Every request has a timeout, and the fake server's "hang" mode proves the timeout works.
- Phase 1 prototype (research R8): if the Pad's fork ignores `checksum`, upload falls back to
  checking size and metadata. The tests cover both paths.
