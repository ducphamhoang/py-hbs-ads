---
phase: 15-daily-board-report-staffing-sections-and-backward
plan: 02
subsystem: reporting
tags: [daily-board-report, staffing-risk, discord, vietnamese, backup-mentions]

requires:
  - phase: 15-01
    provides: Failing tests (RED) for staffing-aware build_report() and format_daily_check_message()

provides:
  - build_report() returns staffing_risks from detect_risks() when snapshot present
  - build_report() returns staffing_risks=None when snapshot absent (COMPAT-01)
  - format_daily_check_message() renders Vietnamese staffing section headers when risks present
  - format_daily_check_message() renders backup Discord token (@@discord_user_id:...@@) for absent-owner tasks
  - All 4 staffing section types rendered: absent+backup, absent+no-backup, overloaded, reduced-bandwidth-overdue

affects:
  - daily_board_report orchestration
  - cron/Discord dispatch consuming format_daily_check_message output

tech-stack:
  added: []
  patterns:
    - "Optional staffing snapshot: guard on exists() before _read_json, result stored in report dict"
    - "Backup mention token always uses mention_style='token' regardless of parent mention_style"
    - "Staffing sections appended at end of lines list, guarded by report.get('staffing_risks')"

key-files:
  created: []
  modified:
    - scripts/notion_scrum/daily_board_report.py

key-decisions:
  - "backup_label always rendered with mention_style='token' (not propagated from parent) — test asserts @@discord_user_id:...@@ regardless of parent style"
  - "staffing_snapshot_path derived from root arg (not hardcoded) to support tmp_path test isolation"
  - "import sys placed inline in except block to avoid polluting module-level imports"

requirements-completed:
  - RPT-01
  - RPT-02
  - RPT-03
  - COMPAT-01

duration: 4min
completed: 2026-04-24
---

# Phase 15 Plan 02: Daily Board Report Staffing Extensions (GREEN) Summary

**Staffing-aware `build_report()` and `format_daily_check_message()` with Vietnamese section headers, backup Discord token mentions, and graceful absent-snapshot fallback**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-24T17:02:15Z
- **Completed:** 2026-04-24T17:06:06Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- `build_report()` now imports `staffing_risk`, loads snapshot from root-relative path when present, calls `detect_risks()`, and stores result in `report["staffing_risks"]` (None when absent)
- `format_daily_check_message()` appends four Vietnamese staffing sections (absent+backup, absent+no-backup, overloaded, reduced-bandwidth-overdue) guarded by `if staffing_risks:`
- Backup owner Discord token `@@discord_user_id:...@@` always rendered in token format for absent-owner task lines (RPT-03)
- All 11 tests pass (7 pre-existing + 4 newly green)

## Task Commits

1. **Task 1: Add staffing_risk import and optional snapshot loading to build_report()** - `dcf2b75` (feat)
2. **Task 2: Extend format_daily_check_message() with staffing sections and backup mentions** - `7981e10` (feat)

## Files Created/Modified

- `scripts/notion_scrum/daily_board_report.py` — Added `import staffing_risk`, snapshot loading in `build_report()`, staffing sections block in `format_daily_check_message()`

## Decisions Made

- **Backup token style always "token":** The test `test_format_daily_check_message_includes_backup_discord_token_for_absent_owner_task` calls `format_daily_check_message` with default `mention_style="discord"` but asserts `@@discord_user_id:...@@` in output. This means backup mentions must always use `mention_style="token"` regardless of the parent's mention_style parameter.
- **`staffing_snapshot_path` derived from `root` arg:** Ensures test isolation via `tmp_path` — tests don't create the snapshot file so the `exists()` guard is False and `_read_json` is never called for the snapshot path, preserving COMPAT-01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Backup label must always use `mention_style="token"` not propagated style**
- **Found during:** Task 2 (extending format_daily_check_message)
- **Issue:** Plan's code sample propagated `mention_style=mention_style` to `_owner_label` for backup_label, but the test calls `format_daily_check_message` with default `"discord"` style and asserts `@@discord_user_id:BOB_DISCORD_ID@@` in output — which requires `mention_style="token"`
- **Fix:** Changed `backup_label` call to hardcode `mention_style="token"`
- **Files modified:** `scripts/notion_scrum/daily_board_report.py`
- **Verification:** `test_format_daily_check_message_includes_backup_discord_token_for_absent_owner_task` passes
- **Committed in:** `7981e10` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Fix necessary for RPT-03 correctness. Backup mentions should be machine-parseable tokens regardless of display context.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 15 complete — all 4 requirements (RPT-01, RPT-02, RPT-03, COMPAT-01) delivered
- All 11 tests green, full suite passes (196 tests)
- Ready for Phase 16 or milestone completion

---
*Phase: 15-daily-board-report-staffing-sections-and-backward*
*Completed: 2026-04-24*
