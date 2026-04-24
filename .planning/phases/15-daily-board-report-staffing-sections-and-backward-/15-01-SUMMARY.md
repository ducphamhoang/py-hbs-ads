---
phase: 15-daily-board-report-staffing-sections-and-backward-
plan: 01
subsystem: testing
tags: [pytest, tdd, staffing, daily-board-report]

requires:
  - phase: 14-staffing-risk-module-and-follow-up-routing
    provides: detect_risks() return structure and staffing_snapshot.json format

provides:
  - 5 new RED-phase failing tests covering RPT-01, RPT-02, RPT-03, COMPAT-01
  - FAKE_RISKS module-level constant reusable across all staffing tests
  - Executable contract for Phase 15 implementation

affects: [15-02, 15-03]

tech-stack:
  added: []
  patterns:
    - "path-conditional _read_json monkeypatch for multi-path disambiguation"
    - "MockClass-as-module pattern for monkeypatching module-level imports"

key-files:
  created: []
  modified:
    - tests/test_notion_scrum_daily_board_report.py

key-decisions:
  - "Test 4 (no_staffing_risks) expected to trivially pass already — plan noted this; added assert confirming test ran"
  - "Used path-conditional lambda for _read_json monkeypatch to avoid registry/snapshot collision"
  - "FAKE_RISKS defined at module level for reuse across all staffing test functions"

patterns-established:
  - "FAKE_RISKS: define shared test fixture constants at module level for cross-test reuse"

requirements-completed:
  - RPT-01
  - RPT-02
  - RPT-03
  - COMPAT-01

duration: 5min
completed: 2026-04-24
---

# Phase 15 Plan 01: RED-Phase Tests for Staffing Sections Summary

**5 TDD RED tests establishing executable contract for build_report() staffing_risks key and format_daily_check_message() staffing section rendering**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-24T17:00:00Z
- **Completed:** 2026-04-24T17:01:40Z
- **Tasks:** 1 (TDD RED phase)
- **Files modified:** 1

## Accomplishments

- FAKE_RISKS constant defined at module level — reusable across all Phase 15 staffing tests
- 4 new tests FAIL (RED) as expected: build_report snapshot absent/present, formatter staffing section, backup discord token
- Test 4 (no_staffing_risks) passes trivially as anticipated in the plan — this is correct behavior
- 6 + 1 = 7 existing tests remain GREEN
- Clear executable contract for Phase 15 GREEN implementation

## Task Commits

1. **Task 1: TDD RED — Write 5 failing tests** - `4d94415` (test)

## Files Created/Modified

- `tests/test_notion_scrum_daily_board_report.py` — Added FAKE_RISKS constant, _minimal_report_base() helper, and 5 new test functions

## Decisions Made

- Test 4 (`with_no_staffing_risks`) was expected per plan to possibly pass already if formatter ignores unknown keys — it does pass. Plan noted this explicitly and said to "add one additional assert to confirm test ran" — done.
- Path-conditional `_read_json` lambda used to disambiguate registry vs snapshot path in test 2.

## Deviations from Plan

None - plan executed exactly as written. 4 of 5 tests FAIL (RED); 1 trivially passes per plan's documented expectation.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED tests committed at `4d94415`
- Phase 15 Plan 02 (GREEN implementation) can proceed: implement `staffing_risks` key in `build_report()` and staffing sections in `format_daily_check_message()`
- Success criteria: all 4 failing tests turn GREEN

---
*Phase: 15-daily-board-report-staffing-sections-and-backward-*
*Completed: 2026-04-24*
