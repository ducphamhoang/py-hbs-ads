---
phase: 14-staffing-risk-module-and-follow-up-routing
plan: "02"
subsystem: api
tags: [tdd, pytest, staffing-risk, follow-up-routing, green-phase, python]

requires:
  - phase: 14-01
    provides: staffing_risk.py stub with NotImplementedError signatures + 10 failing tests

provides:
  - Full implementation of detect_risks() covering RISK-01..05
  - Full implementation of compute_routing_recommendation() covering ROUT-01..04
  - All 10 staffing risk tests passing green

affects:
  - 15-staffing-risk-module-and-follow-up-routing
  - Any phase consuming staffing risk output or follow-up routing

tech-stack:
  added: []
  patterns:
    - "TDD GREEN: replace NotImplementedError stubs with minimal implementations to pass tests"
    - "people_state_store.effective_followup_target() as primary routing; snapshot fallback when people_state is None"
    - "Stable sort on all risk lists (by person_key / task_id / project_id)"

key-files:
  created: []
  modified:
    - scripts/notion_scrum/staffing_risk.py

key-decisions:
  - "RISK-02 project title resolved by index from person['active_project_ids'] / ['active_project_titles'] — not from project_effective_owners (no title field there)"
  - "RISK-04 overload check uses no availability_status or risk_flags — pure count threshold check"
  - "compute_routing_recommendation always returns recommendation_only: True regardless of routing path"

patterns-established:
  - "Routing fallback pattern: people_state is not None → call people_state_store; else derive from snapshot availability_status"

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

# Phase 14 Plan 02: Staffing Risk Module GREEN Phase Summary

**TDD GREEN phase: full implementation of detect_risks() (5 RISK categories) and compute_routing_recommendation() (snapshot fallback + people_state routing) — all 10 tests pass, 191 total tests green**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-24T16:33:48Z
- **Completed:** 2026-04-24T16:35:42Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `detect_risks()` covering all 5 risk categories with stable sorting
- Implemented `compute_routing_recommendation()` with people_state-aware routing and snapshot fallback
- `recommendation_only: True` enforced in all return paths
- All 10 tests in `test_notion_scrum_staffing_risk.py` pass; no regressions in 191-test suite

## Task Commits

Each task was committed atomically:

1. **Task 1+2: Implement detect_risks and compute_routing_recommendation** - `f7abf82` (feat)

**Plan metadata:** _(docs commit pending)_

## Files Created/Modified

- `scripts/notion_scrum/staffing_risk.py` — Full implementation replacing NotImplementedError stubs

## Decisions Made

- RISK-02 project title resolved by index lookup in `person["active_project_ids"]` / `["active_project_titles"]` (project_effective_owners has no title field)
- RISK-04 overload check is pure count threshold — no availability_status or risk_flags check
- Both tasks committed together since they're in the same file and both required for all 10 tests to pass

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GREEN phase complete: staffing_risk.py fully implemented and tested
- All 9 requirements (RISK-01..05, ROUT-01..04) satisfied
- Ready for Phase 15 which will consume the risk detection and routing outputs
- No blockers

---
*Phase: 14-staffing-risk-module-and-follow-up-routing*
*Completed: 2026-04-24*
