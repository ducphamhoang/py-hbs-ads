---
phase: "11"
plan: "01"
subsystem: "people-state"
tags: [tdd, testing, people-state, red-phase]
dependency_graph:
  requires: []
  provides:
    - tests/test_notion_scrum_people_state.py
  affects:
    - scripts/notion_scrum/people_state_store.py (plan 11-02, must satisfy these tests)
    - scripts/notion_scrum/result_contracts.py (plan 11-03, must add staffing fields)
tech_stack:
  added: []
  patterns:
    - inline helper pattern (no conftest.py)
    - tmp_path fixture for all file I/O
    - sys.path.insert to import scripts/notion_scrum modules
key_files:
  created:
    - tests/test_notion_scrum_people_state.py
  modified: []
decisions:
  - "_make_person helper created with full PRD §10.1 person record skeleton to avoid repetition"
  - "16 test functions covering all requirements; since/until cleared = None (not absent) per clear_leave contract"
metrics:
  duration: "84s"
  completed: "2026-04-24"
  tasks_completed: 1
  files_changed: 1
---

# Phase 11 Plan 01: People-State Failing Tests (RED Phase) Summary

**One-liner:** Failing test suite for people_state_store module covering all 11 Phase 11 requirements (STATE-01..STATE-10, COMPAT-02) with 16 named test functions — all fail with ModuleNotFoundError.

## What Was Built

A single test file `tests/test_notion_scrum_people_state.py` containing 16 test functions that define the behavioral contract for `people_state_store.py` (to be implemented in plan 11-02) and the result-contract extension in `result_contracts.py` (plan 11-03).

All tests fail at collection time with `ModuleNotFoundError: No module named 'people_state_store'` — confirming RED state.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing test file (RED phase) | 0a82e21 | tests/test_notion_scrum_people_state.py (created, 431 lines) |

## Test Coverage Map

| Req ID | Test Function | Status |
|--------|---------------|--------|
| STATE-01 | test_load_save_valid_container | RED |
| COMPAT-02 | test_load_missing_file_returns_empty_container | RED |
| STATE-02 | test_validate_rejects_invalid_status | RED |
| STATE-03 | test_validate_rejects_invalid_bandwidth | RED |
| STATE-04 | test_validate_rejects_invalid_date_window | RED |
| STATE-05 | test_validate_rejects_unknown_backup_key | RED |
| STATE-06 | test_set_leave_transition | RED |
| STATE-07 | test_clear_leave_transition | RED |
| STATE-08a | test_set_bandwidth_transition | RED |
| STATE-08b | test_set_backup_transition | RED |
| STATE-09a | test_is_person_absent | RED |
| STATE-09b | test_effective_followup_target_active | RED |
| STATE-09c | test_effective_followup_target_leave_with_backup | RED |
| STATE-09d | test_effective_followup_target_leave_no_backup | RED |
| STATE-09e | test_effective_followup_target_missing_person | RED |
| STATE-10 | test_result_envelope_includes_staffing_fields | RED |

## Inline Helpers Created

- `_sample_registry(tmp_path)` — writes minimal team_registry.json with ducph and toanvt entries
- `_empty_container()` — returns `{"schema_version": "1.0", "updated_at": ..., "people": {}}`
- `_sample_source()` — returns valid source attribution object
- `_make_person(status, bandwidth, backup_key, since, until)` — returns full PRD §10.1 person record dict

## Deviations from Plan

None — plan executed exactly as written.

- Helper `_make_person` added as specified in the action block (not a deviation).
- 16 test functions created (matches required count exactly).
- All tests use `_sample_source()` helper instead of inline dicts to keep test functions readable.

## Known Stubs

None — this is a test-only file. No stubs that would prevent plan goal achievement. Tests are intentionally failing (RED phase).

## Threat Flags

None — test file introduces no new network endpoints, auth paths, or trust-boundary surface. Uses `sys.path.insert` per project-standard pattern (T-11-01 accepted).

## Self-Check: PASSED

- [x] `tests/test_notion_scrum_people_state.py` exists: FOUND
- [x] Commit `0a82e21` exists: FOUND
- [x] `grep -c "^def test_" tests/test_notion_scrum_people_state.py` = 16
- [x] `python3 -m pytest tests/test_notion_scrum_people_state.py 2>&1 | grep ModuleNotFoundError` exits 0 (RED confirmed)
- [x] Syntax check: `python3 -c "import ast; ast.parse(...)"` exits 0
