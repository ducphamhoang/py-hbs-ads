---
phase: "11"
plan: "02"
subsystem: "people-state"
tags: [tdd, green-phase, people-state, store-module, result-contracts]
dependency_graph:
  requires:
    - tests/test_notion_scrum_people_state.py (plan 11-01, RED phase tests)
    - scripts/notion_scrum/common.py (load_json, save_json, utc_now_iso)
  provides:
    - scripts/notion_scrum/people_state_store.py
    - scripts/notion_scrum/result_contracts.py (staffing fields added)
  affects:
    - Phase 12+ operator CLI scripts (import people_state_store)
    - Phase 12+ result envelopes (effective_followup_person_key, routing_reason)
tech_stack:
  added: []
  patterns:
    - pure-function store module (no class, no singleton)
    - from common import load_json, save_json, utc_now_iso
    - validate_* returns list[str] — empty = valid
    - transition functions modify in-place and return data (caller saves)
    - _ensure_person private helper for lazy person record creation
key_files:
  created:
    - scripts/notion_scrum/people_state_store.py
  modified:
    - scripts/notion_scrum/result_contracts.py
decisions:
  - "Extended result_contracts.py in plan 11-02 (not 11-03) because STATE-10 test is in the 11-02 test suite — deviation Rule 2"
  - "VALID_STATUSES and VALID_BANDWIDTHS are frozensets for immutability and O(1) membership tests"
  - "_ensure_person inserts full blank record skeleton so all transition functions can .update() sub-dicts safely"
  - "load_people_state uses load_json default= parameter to return empty container without raising on missing file"
  - "effective_followup_target checks both availability.backup_person_key and coordination.backup_person_key as fallback"
metrics:
  duration: "~4m"
  completed: "2026-04-24"
  tasks_completed: 1
  files_changed: 2
---

# Phase 11 Plan 02: People-State Store Module (GREEN Phase) Summary

**One-liner:** people_state_store.py with 10 public functions + 2 constants implements the full people-state store contract; all 16 RED-phase tests now pass GREEN.

## What Was Built

`scripts/notion_scrum/people_state_store.py` — the shared store module for all Phase 12+ staffing-aware automation. Follows the same pure-function dict pattern as `prompt_store.py`:

- `VALID_STATUSES` / `VALID_BANDWIDTHS` — frozenset constants for enum validation
- `_ensure_person` — private helper that lazily inserts a blank person record with all sub-objects initialized
- `load_people_state` — calls `load_json` with a default empty container so missing files never raise
- `save_people_state` — delegates to `save_json` for atomic writes
- `validate_people_state` — checks status enum, bandwidth enum, date window inversion, and optional backup key against registry; returns `list[str]`
- `set_leave` / `clear_leave` / `set_bandwidth` / `set_backup` — pure transition functions that modify data in-place, stamp `updated_at`, and return the modified container
- `get_person_state` — safe accessor returning None for unknown keys
- `is_person_absent` — True only for `leave` / `ooo` status
- `effective_followup_target` — four-case routing returning `(target_key, routing_reason)` tuple

`scripts/notion_scrum/result_contracts.py` was also extended with `effective_followup_person_key` and `routing_reason` fields (see Deviations).

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement people_state_store.py (GREEN phase) | 1b36905 | scripts/notion_scrum/people_state_store.py (created, 218 lines); scripts/notion_scrum/result_contracts.py (modified) |

## Test Coverage Map

| Req ID | Test Function | Status |
|--------|---------------|--------|
| STATE-01 | test_load_save_valid_container | GREEN |
| COMPAT-02 | test_load_missing_file_returns_empty_container | GREEN |
| STATE-02 | test_validate_rejects_invalid_status | GREEN |
| STATE-03 | test_validate_rejects_invalid_bandwidth | GREEN |
| STATE-04 | test_validate_rejects_invalid_date_window | GREEN |
| STATE-05 | test_validate_rejects_unknown_backup_key | GREEN |
| STATE-06 | test_set_leave_transition | GREEN |
| STATE-07 | test_clear_leave_transition | GREEN |
| STATE-08a | test_set_bandwidth_transition | GREEN |
| STATE-08b | test_set_backup_transition | GREEN |
| STATE-09a | test_is_person_absent | GREEN |
| STATE-09b | test_effective_followup_target_active | GREEN |
| STATE-09c | test_effective_followup_target_leave_with_backup | GREEN |
| STATE-09d | test_effective_followup_target_leave_no_backup | GREEN |
| STATE-09e | test_effective_followup_target_missing_person | GREEN |
| STATE-10 | test_result_envelope_includes_staffing_fields | GREEN |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added staffing fields to result_contracts.py**
- **Found during:** Task 1 — `test_result_envelope_includes_staffing_fields` (STATE-10) failed because `effective_followup_person_key` and `routing_reason` were absent from `RESULT_KEYS` and `build_result`
- **Issue:** Plan 11-02's test suite includes STATE-10 which requires result_contracts.py changes planned for 11-03. The test was in scope for this GREEN phase.
- **Fix:** Added `effective_followup_person_key: str | None = None` and `routing_reason: str = "unknown"` to `RESULT_KEYS` tuple and `build_result` function signature/return dict
- **Files modified:** `scripts/notion_scrum/result_contracts.py`
- **Commit:** 1b36905 (same commit as people_state_store.py)

## Known Stubs

None — all functions are fully implemented. No hardcoded empty values that flow to callers.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surface beyond what was in the plan's threat model (T-11-03 through T-11-06 all addressed by implementation).

## Self-Check: PASSED

- [x] `scripts/notion_scrum/people_state_store.py` exists: FOUND
- [x] Commit `1b36905` exists: FOUND
- [x] `python3 -m pytest tests/test_notion_scrum_people_state.py -x` = 16 passed
- [x] `grep -c "^def " scripts/notion_scrum/people_state_store.py` = 11 (1 private + 10 public)
- [x] No third-party imports in people_state_store.py
- [x] `grep "from common import load_json, save_json, utc_now_iso"` exits 0
- [x] All acceptance criteria met
