# Log Record Contract

File: `<log.dir>/<tool>.jsonl`, UTF-8, one JSON object per line, `\n` line endings.

```json
{"ts":"2026-11-02T14:03:11.402Z","level":"ERROR","tool":"upload","event":"checksum_mismatch","run_id":"3f0c…","msg":"Pad rejected upload","details":{"file":"build/bracket.gcode","sha256":"ab12…","status":422}}
```

| Field     | Required | Notes                                         |
| :-------- | :------- | :-------------------------------------------- |
| `ts`      | yes      | UTC, millisecond precision, `Z` suffix         |
| `level`   | yes      | `DEBUG` `INFO` `WARNING` `ERROR`               |
| `tool`    | yes      | matches the file name                          |
| `event`   | yes      | stable snake_case identifier, listed below     |
| `run_id`  | yes      | UUID4                                          |
| `msg`     | yes      | ≤ 200 chars                                    |
| `details` | no       | object; secrets masked as `***`                |

Core events (tools may add more, but must not rename these):

`run_start`, `run_end`, `config_loaded`, `config_invalid`, `http_request`, `http_error`,
`host_unreachable`, `upload_ok`, `checksum_mismatch`, `slice_ok`, `slice_failed`, `export_ok`,
`export_failed`, `state_change`, `alert_sent`, `notify_failed`, `watch_started`, `watch_resumed`, `watch_stopped`,
`prune_done`, `backup_committed`, `backup_no_change`, `secret_scan_failed`.

Query examples:

```bash
jq -c 'select(.level=="ERROR")' ~/.local/state/cr10s/*.jsonl
jq -c 'select(.run_id=="3f0c…")' ~/.local/state/cr10s/*.jsonl | sort
```
