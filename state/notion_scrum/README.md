# Hermes Notion Scrum Runtime State

This directory holds local runtime state for the Hermes Discord <-> Notion Scrum workflow.

The live files are intentionally not committed:

- `team_registry.json`
- `pending_prompts.json`
- `audit_log.jsonl`

They may contain Discord user IDs, Notion user/page IDs, emails, prompt history, audit events, and other operational context. Treat them as local operator state, not source code.

Use the committed `*.example.json` and `*.example.jsonl` files as bootstrap shapes. Copy them to the live filenames only for a local environment, then replace placeholder values with real workspace data.

Board/channel defaults are bootstrapped separately from:
- `config/notion_scrum/board_config.example.json`

Copy that file to `config/notion_scrum/board_config.json` for local use, then fill in the real Notion data source IDs and Discord channel defaults for the workspace.

For runnable sample flows, use the sanitized fixtures in `scripts/notion_scrum/samples/`.

Before applying writes to Notion, run preflight against the local files:

```bash
PYTHONPATH=scripts/notion_scrum python3 scripts/notion_scrum/preflight.py
```

Live write behavior should be driven by the local runtime state plus an explicit `--execute` invocation on the relevant command.
