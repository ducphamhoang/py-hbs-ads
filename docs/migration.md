# Migration And Cutover Runbook

## Goal

Migrate from `~/work/hbs-ads` to the Python rewrite incrementally, with explicit verification and rollback points.

## Preconditions

- Python `3.12+`
- Local editable install working: `python3 -m pip install -e .[dev]`
- Operators understand the workspace conventions in `docs/operator_guide.md`
- Any external tool dependencies required by the selected workflow are installed

## Recommended Rollout Order

1. Bootstrap and workspace verification
2. Ingest and trim
3. Tagging and approval
4. Variant generation and export
5. Reporting and notifications
6. SharePoint and voiceover adapters if needed for the job

This keeps the earliest cutover steps focused on the most repeatable local workflows before moving to environment-sensitive integrations.

## Side-By-Side Validation

For a candidate job workspace:

1. Create a new Python workspace.
2. Stage a representative subset of the same source inputs used in the current repo.
3. Run dry-run checks first:

```bash
hbs-ads --workspace /path/to/job ingest run --dry-run
hbs-ads --workspace /path/to/job trim run --config cuts.json --dry-run
hbs-ads --workspace /path/to/job pipeline run --dry-run --json
```

4. Run the live Python commands for the selected slice.
5. Compare:
   - produced files under `_ASSETS`, `_HOOKS`, `VARIANTS`, `reports`, and `logs`
   - local SQLite state
   - operator-facing CLI output or JSON payloads

## Rollback

Rollback is phase-based, not all-or-nothing:

- If bootstrap or foundation verification fails, keep using `~/work/hbs-ads` for that workspace.
- If a migrated slice fails, stop at that slice and keep the remaining workflow on the current repo.
- Keep job workspaces isolated so Python-generated artifacts do not overwrite the legacy repo state.

## Known Gaps

- Live SharePoint behavior is not verified in v1; local transfer verification is file-backed.
- Live AI and voiceover providers are not exercised in CI.
- Scheduler-style behavior such as `ingest watch` and cron installation remains intentionally shallow.
- Media-binary parity beyond fixture-driven workflows still depends on the local `ffmpeg` toolchain.

## Phase 6 Completion Standard

Phase 6 should be considered complete when:

- `python3 -m pytest` passes
- representative operator commands pass in both text and JSON mode
- legacy-style workspace-relative variant configs are proven in tests
- remaining live-integration gaps are documented instead of implied away
