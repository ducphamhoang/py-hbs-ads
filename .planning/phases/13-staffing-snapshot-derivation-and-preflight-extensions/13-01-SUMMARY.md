---
phase: 13
plan: "01"
subsystem: staffing-snapshot-derivation
tags:
  - tdd
  - red-state
  - contract-locking
  - test-first
dependency_graph:
  requires:
    - Phase 11 (people-state schema and store)
    - Phase 12 (operator CLI interfaces)
  provides:
    - Locked snapshot builder contract (SNAP-01..04)
    - Locked preflight staffing extension contract (PRE-01..04)
    - RED test suite as executable specification
  affects:
    - Phase 02 (snapshot builder implementation)
    - Phase 03 (preflight extension implementation)
tech_stack:
  added:
    - pytest fixture patterns for snapshot derivation
    - Snapshot schema contract (schema_version, generated_at, inputs, people, project_effective_owners)
  patterns:
    - Inline helper builders (no decorators) following test_notion_scrum_people_state.py pattern
    - Module import via sys.path injection following test_notion_scrum_board_cache.py pattern
    - Local JSON fixtures for registry, board snapshot, people state
  removed: []
key_files:
  created:
    - tests/test_notion_scrum_staffing_snapshot.py (11 test functions)
    - tests/test_notion_scrum_preflight.py (7 test functions)
  modified: []
decisions:
  - Active-status vocabulary locked: Not started + In progress = active; Done + Archived = inactive
  - Blocked detection rule: blocked_reason is non-empty OR status == "Blocked"
  - Overdue detection: active task with due_date < today_iso
  - Undated detection: active task with due_date is None
  - Unresolved owner IDs must be preserved explicitly in snapshot (not silently dropped)
  - Preflight staffing checks are additive (preserve existing registry/prompt validation)
  - Missing people_state.json is a warning for read-only workflows, error for staffing-aware
duration_minutes: 1
completed_date: "2026-04-24"
---

# Phase 13 Plan 01: Staffing Snapshot & Preflight Test Suite (RED)

## Summary

Locked the behavioral contract for Phase 13 by writing a complete failing test suite before any implementation exists. Two new dedicated test files — one for the snapshot builder (SNAP-01..04) and one for the preflight staffing extension (PRE-01..04) — pin the exact function signatures, fixture shapes, assertion targets, and warning/error boundaries the implementation must satisfy.

**Status:** RED ✗ — Both test files fail as expected. Snapshot tests fail with `ModuleNotFoundError` (import build_staffing_snapshot fails). Preflight tests fail with `TypeError` (new kwargs don't exist on current preflight.run_preflight).

## Files Created

### tests/test_notion_scrum_staffing_snapshot.py

**11 test functions covering SNAP-01 through SNAP-04:**

1. `test_build_snapshot_from_registry_people_board` — Snapshot builder signature and basic output structure
2. `test_snapshot_person_record_shape` — Per-person record has all required fields (canonical_person_key, display_name, availability_status, leave_since/until, backup_person_key, active_project_ids, active_project_titles, active_task_ids, active_task_titles, active_projects, active_tasks, blocked_tasks, overdue_tasks, undated_tasks, risk_flags)
3. `test_assignments_from_board_cache_and_registry_only` — Assignments derive from board owner IDs + registry mappings only, not manual people_state entries
4. `test_project_effective_owners_with_leave_backup` — project_effective_owners map with leave/backup substitution (SNAP-04)
5. `test_missing_people_state_builds_unknown_availability` — Empty people_state produces snapshot with availability_status="unknown"
6. `test_absent_owner_with_backup_yields_effective_owner` — Absence + backup = effective owner substitution
7. `test_unresolved_owner_ids_preserved_in_snapshot` — Unresolved board owner IDs (not in registry) are preserved explicitly in snapshot (not dropped)
8. `test_overdue_blocked_undated_counts_from_board_cache` — Task counts (overdue, blocked, undated) derive from board cache status/due_date
9. `test_snapshot_has_required_top_level_schema` — Snapshot has schema_version=1.0, generated_at (ISO timestamp), inputs (with registry_source, people_state_source, board_snapshot_source), people dict, project_effective_owners dict
10. `test_display_name_prefers_registry_notion_name` — display_name prefers registry notion.display_name when present
11. `test_empty_board_snapshot_lists_all_registry_people_with_zero_assignments` — Empty board snapshot still lists all registry people with assignment counts=0

**Inline fixture helpers (matching test_notion_scrum_people_state.py pattern):**

- `_sample_registry()` — Registry with person1 (notion.user_id="00000000-0000-4000-8000-000000000001", notion.display_name="Person One (P1)") and person2
- `_sample_board_snapshot_mixed()` — Board snapshot with 2 projects, 4 tasks covering active/done/archived statuses, overdue/undated/blocked cases, and unresolved owner IDs
- `_empty_people_state()` — Valid empty people_state container
- `_people_state_with_leave()` — person1 on leave until 2026-05-01 with backup=person2

### tests/test_notion_scrum_preflight.py

**7 test functions covering PRE-01 through PRE-04:**

1. `test_preflight_missing_people_state_is_warning` — Missing people_state.json returns warning (result["ok"]=True) when require_people_state=False
2. `test_preflight_invalid_people_state_version_is_error` — Invalid schema_version returns error (result["ok"]=False) when require_people_state=True
3. `test_preflight_malformed_people_state_json_is_error` — Malformed JSON returns error
4. `test_preflight_unknown_backup_key_is_error` — Backup person key not in registry returns error
5. `test_preflight_invalid_leave_dates_is_error` — Inverted leave date window (until < since) returns error
6. `test_preflight_legacy_registry_and_prompt_checks_still_run` — Regression test: existing registry and prompt validation still runs without regression
7. `test_preflight_success_preserves_stable_envelope_with_staffing` — Success case preserves stable result envelope (result.keys() == result_contracts.RESULT_KEYS)

**Inline fixture helpers (matching test_notion_scrum_update_people_state.py pattern):**

- `_write_registry(tmp_path)` — Write minimal valid team_registry.json with person1
- `_write_empty_prompts(tmp_path)` — Write empty pending_prompts.json
- `_write_people_state(tmp_path, data)` — Write people_state.json with given data
- `_valid_people_state_with_person1_active()` — Valid people_state with person1 in active availability

**Test calls extended preflight signature:**

```python
result = preflight.run_preflight(
    registry_path=...,
    state_path=...,
    audit_log_path=...,
    people_state_path=...,          # NEW (Plan 03 adds this)
    require_people_state=...,        # NEW (Plan 03 adds this)
)
```

These new kwargs cause `TypeError: unexpected keyword argument` in current implementation (correct RED state).

## Snapshot Fixture Data Contract

### Active-Status Vocabulary (locked in test comments)

- **Active projects:** status NOT IN ("Done", "Archived") → {Not started, In progress}
- **Active tasks:** status NOT IN ("Done", "Archived") → {Not started, In progress}
- **Blocked tasks:** blocked_reason is non-empty string OR status == "Blocked"
- **Overdue tasks:** active task with due_date < today_iso
- **Undated tasks:** active task with due_date is None

### Unresolved Owner IDs Location

Tests assert unresolved owner IDs (Notion user IDs not mapped to any registry canonical person) appear explicitly in:
- `snapshot["unresolved_owner_ids"]` (top-level list), OR
- `snapshot["meta"]["unresolved_owner_ids"]` (nested in meta)

**Must not be silently dropped.** Current live board snapshot contains unresolved owner IDs (21 project owners, 47 task owners unmapped), so this is a real correctness requirement.

### Fixture Person Keys

- `person1`: Notion user_id = "00000000-0000-4000-8000-000000000001", display_name = "Person One (P1)"
- `person2`: Notion user_id = "00000000-0000-4000-8000-000000000002", display_name = None (falls back to canonical key)
- Unresolved IDs: "notion-user-unresolved-xyz", "notion-user-unresolved-999"

## RED Confirmation

### Snapshot Tests (test_notion_scrum_staffing_snapshot.py)

```
ERROR collecting tests/test_notion_scrum_staffing_snapshot.py
ModuleNotFoundError: No module named 'build_staffing_snapshot'
```

✓ Test file exists  
✓ 11 test functions defined (verified by grep)  
✓ Correct RED state: import fails  
✓ Inline helper fixtures present  
✓ Active-status vocabulary documented in comments  

### Preflight Tests (test_notion_scrum_preflight.py)

```
FFFFFFF [7 failures]
TypeError: run_preflight() got an unexpected keyword argument 'people_state_path'
```

✓ Test file exists  
✓ 7 test functions defined (verified by grep)  
✓ Correct RED state: new kwargs cause TypeError  
✓ Inline helper fixtures present  

### Existing Test Suite (GREEN baseline)

```
tests/test_notion_scrum_board_cache.py
tests/test_notion_scrum_people_state.py
tests/test_notion_scrum.py
========== 56 passed in 0.07s ==========
```

✓ board-cache tests still pass (14 tests)  
✓ people-state tests still pass (7 tests)  
✓ preflight/main tests still pass (35 tests)  
✓ No regression  

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

### RED Gate (Completed)

- **Commit:** `e0b7f60` (snapshot tests) + `c6ee9e4` (preflight tests)
- **Test status:** Both files fail on import (snapshot) and kwargs (preflight) as intended
- **Test count:** 11 + 7 = 18 test functions total
- **Fixture patterns:** Inline helpers with no @pytest.fixture decorators, matching existing test style

### GREEN Gate (Deferred to Plan 02 & 03)

- Plan 02: Implement `scripts/notion_scrum/build_staffing_snapshot.py` → snapshot tests turn GREEN
- Plan 03: Extend `scripts/notion_scrum/preflight.py` with people_state_path + require_people_state kwargs → preflight tests turn GREEN

## Key Decisions

1. **Active-status vocabulary:** Not started + In progress are active; Done + Archived are inactive. Locked in test comments and assertions.
2. **Blocked detection:** `blocked_reason` is non-empty string OR `status == "Blocked"` (union, not exclusive).
3. **Unresolved owner handling:** Explicit preservation required. Tests assert unresolved IDs appear in snapshot output (top-level or meta).
4. **Preflight additive extension:** New kwargs optional (default missing people_state, require_people_state=False) so existing callers don't break.
5. **Missing vs invalid people_state:** Missing file = warning (PRE-01), invalid file = error (PRE-02..04). Tests lock this boundary.

## Known Stubs

None — test file contains complete test bodies with assertions, not just `pass` stubs.

## Test Execution Commands

**Per-task verification:**
```bash
python3 -m pytest tests/test_notion_scrum_staffing_snapshot.py -q  # RED (fails on import)
python3 -m pytest tests/test_notion_scrum_preflight.py -q          # RED (fails on TypeError)
```

**Regression baseline:**
```bash
python3 -m pytest tests/test_notion_scrum_board_cache.py tests/test_notion_scrum_people_state.py tests/test_notion_scrum.py -q
# Expected: 56 passed
```

**Full staffing suite (after Plans 02 & 03):**
```bash
python3 -m pytest tests/test_notion_scrum_board_cache.py tests/test_notion_scrum_people_state.py tests/test_notion_scrum.py tests/test_notion_scrum_staffing_snapshot.py tests/test_notion_scrum_preflight.py -q
# Expected after GREEN: 56 + 18 = 74+ passed
```

## Architecture Notes

### Snapshot Builder Contract

- **Function:** `build_staffing_snapshot.build_staffing_snapshot(registry, people_state, board_snapshot, today_iso="2026-04-24") -> dict`
- **Input:** Three local JSON-compatible dicts (no Notion API calls)
- **Output:** Snapshot dict with schema_version, generated_at, inputs, people, project_effective_owners
- **Per-person fields:** At least 16 (canonical_person_key, display_name, availability_status, leave_since, leave_until, bandwidth, backup_person_key, active_project_ids, active_project_titles, active_task_ids, active_task_titles, active_projects, active_tasks, blocked_tasks, overdue_tasks, undated_tasks, plus risk_flags)
- **Edge case:** Empty board snapshot or missing people_state must not crash; builds valid snapshot with known counts or "unknown" availability

### Preflight Extension Contract

- **Current signature:** `preflight.run_preflight(registry_path, state_path, audit_log_path) -> dict`
- **Extended signature (Plan 03):** Add `people_state_path: Path | None = None, require_people_state: bool = False`
- **Behavior:** When require_people_state=False (default) and file missing, append warning. When require_people_state=True or file present, validate and error on invalid schema/backup/dates.
- **Result envelope:** Preserve all keys from `result_contracts.RESULT_KEYS`; append staffing errors/warnings under `result["errors"]` and `result["data"]["warnings"]`

## Next Steps

1. **Plan 02:** Implement `scripts/notion_scrum/build_staffing_snapshot.py` → turn snapshot tests GREEN
2. **Plan 03:** Extend `scripts/notion_scrum/preflight.py` with new kwargs + staffing validation → turn preflight tests GREEN
3. **Verification:** All 18 new tests pass + existing 56 tests remain green

---

*Plan 13-01 complete. RED test suite written. Ready for Plan 02 implementation.*
