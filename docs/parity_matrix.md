# Parity Matrix

## Purpose

This matrix records what the Python rewrite currently verifies, what remains partial, and what is intentionally deferred for a later phase or live-environment check.

## Command Coverage

| Command Area | Status | Evidence | Notes |
|--------------|--------|----------|-------|
| `init workspace`, `init db` | Verified | `tests/test_cli.py`, `tests/test_workflows.py` | Workspace and SQLite bootstrap are covered. |
| `assets list` | Verified | `tests/test_cli.py` | Basic inventory listing is covered. |
| `ingest run` | Verified | `tests/test_workflows.py` | Copies inbox files into `_ASSETS/raw` and records DB state. |
| `ingest watch`, `ingest cron` | Partial | CLI contract only | Still scaffold behavior, but exposed intentionally. |
| `trim run`, `trim clip` | Verified | `tests/test_workflows.py` | Dry-run behavior and config execution are covered. |
| `tag auto`, `tag ai`, `tag approve`, `tag pending` | Verified | `tests/test_workflows.py` | Approval state and pending review behavior are covered. |
| `variants generate`, `assemble`, `export`, `validate`, `archive` | Verified | `tests/test_workflows.py`, `tests/test_phase6_parity.py` | Includes legacy-style config path smoke coverage. |
| `hooks assemble` | Verified | `tests/test_workflows.py` | Approved clips can produce hook assets. |
| `pipeline run` | Verified | `tests/test_cli.py`, `tests/test_workflows.py` | Review gate and full-mode completion are covered. |
| `sharepoint setup`, `upload`, `download` | Verified | `tests/test_workflows.py` | Local file-backed transfer flow is covered. |
| `competitor analyze`, `report` | Verified | `tests/test_workflows.py` | Deterministic report generation is covered. |
| `perf ingest`, `report` | Verified | `tests/test_workflows.py` | CSV ingestion and roll-up reporting are covered. |
| `notify render-done`, `progress` | Verified | `tests/test_workflows.py` | Dry-run and live log writes are covered. |
| `voiceover generate` | Verified | `tests/test_workflows.py` | Deterministic transcript, manifest, and audio placeholders are covered. |
| Text, JSON, and quiet output modes | Verified | `tests/test_outputs.py`, `tests/test_cli.py` | Success and error JSON payloads are tested. |
| Module entrypoint invocation | Verified | `tests/test_cli.py` | `python -m hbs_ads.cli.main --help` is covered. |

## Partial Or Deferred Areas

| Area | Status | Reason |
|------|--------|--------|
| Live SharePoint auth and API behavior | Deferred | Current Phase 5/6 implementation uses a file-backed seam for repeatable local verification. |
| Live AI provider behavior | Deferred | The rewrite keeps provider seams explicit but does not require network-backed tests in v1. |
| Real `ffmpeg` and `ffprobe` parity | Partial | Adapter boundaries exist; fixture-driven workflow tests do not require full media binaries yet. |
| `ingest watch` and cron scheduling | Partial | CLI surface is preserved, but production scheduling behavior is not implemented in v1. |
