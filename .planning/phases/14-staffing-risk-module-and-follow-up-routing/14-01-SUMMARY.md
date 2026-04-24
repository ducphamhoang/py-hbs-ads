---
phase: 14-staffing-risk-module-and-follow-up-routing
plan: "01"
subsystem: testing
tags: [tdd, pytest, staffing-risk, follow-up-routing, red-phase]

requires: []
provides:
  - staffing_risk.py stub with NotImplementedError signatures for detect_risks and compute_routing_recommendation
  - 10 failing test functions covering RISK-01..05 and ROUT-01..04 requirements
affects:
  - 14-staffing-risk-module-and-follow-up-routing

tech-stack:
  added: []
  patterns:
    - "Inline helper builder pattern (no @pytest.fixture) — matches existing test_notion_scrum_staffing_snapshot.py style"
    - "sys.path.insert with ROOT/scripts/notion_scrum for module isolation"

key-files:
  created:
    - scripts/notion_scrum/staffing_risk.py
    - tests/test_notion_scrum_staffing_risk.py
  modified: []

key-decisions:
  - "Tests written to assert on return values (not using pytest.raises(NotImplementedError)) — all 10 show as FAILED not ERROR, which is acceptable RED phase behavior"
  - "No main() entrypoint added to stub — GREEN phase will add implementation only"

patterns-established:
  - "TDD RED: stub module raises NotImplementedError; test suite asserts expected dict structure → all FAILED at runtime"

requirements-completed:
  - RISK-01
  - RISK-02
  - RISK-03
  - RISK-04
  - RISK-05
  - ROUT-01
  - ROUT-02
  - ROUT-03
  - ROUT-04

duration: 2min
completed: 2026-04-24
---

# Phase 14 Plan 01: Staffing Risk Module RED Phase Summary

**TDD RED phase: staffing_risk.py stub with NotImplementedError signatures + 10 failing test functions covering all 9 requirements (RISK-01..05, ROUT-01..04)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-24T16:29:23Z
- **Completed:** 2026-04-24T16:31:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created importable `staffing_risk.py` stub with `detect_risks` and `compute_routing_recommendation` raising `NotImplementedError`
- Created `tests/test_notion_scrum_staffing_risk.py` with 10 named test functions (RISK-01..05, ROUT-01..04 + threshold override)
- All 10 tests FAILED (not collection errors) — RED phase contract established
- No regression: 181 existing non-integration tests still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create staffing_risk.py stub module** - `344cba2` (test)
2. **Task 2: Create failing test suite for all 9 requirements** - `278bb54` (test)

**Plan metadata:** _(docs commit pending)_

## Files Created/Modified

- `scripts/notion_scrum/staffing_risk.py` — Stub module with two NotImplementedError functions
- `tests/test_notion_scrum_staffing_risk.py` — 10 failing tests with inline helpers

## Decisions Made

- Tests assert on expected return dict structure rather than using `pytest.raises(NotImplementedError)` — this causes all tests to show as FAILED (not PASSED), which is the correct RED phase state
- No `main()` entrypoint added to stub — GREEN phase will add full implementation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED phase complete: test contract locked for RISK-01..05 and ROUT-01..04
- Ready for GREEN phase (14-02): implement `detect_risks` and `compute_routing_recommendation` to make all 10 tests pass
- No blockers

---
*Phase: 14-staffing-risk-module-and-follow-up-routing*
*Completed: 2026-04-24*
