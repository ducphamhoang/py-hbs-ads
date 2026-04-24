---
phase: 13
plan: "03"
subsystem: preflight-staffing-extension
tags:
  - tdd
  - green-state
  - preflight
  - people-state
dependency_graph:
  requires:
    - Phase 13 Plan 01 (RED test suite: 7 failing preflight tests)
    - Phase 11 (people_state_store.validate_people_state)
  provides:
    - Extended run_preflight with additive staffing integrity checks (PRE-01..04)
    - 7 PRE tests GREEN
  affects:
    - scripts/notion_scrum/preflight.py
    - tests/test_notion_scrum_preflight.py
tech_stack:
  added:
    - people_state_store import in preflight.py
    - DEFAULT_PEOPLE_STATE constant derived from DEFAULT_STATE_DIR
  patterns:
    - Additive staffing check block after existing registry/prompt checks
    - Schema-version gate before validate_people_state delegation
    - JSONDecodeError/ValueError catch for malformed-file safety
  removed: []
key_files:
  created: []
  modified:
    - scripts/notion_scrum/preflight.py
    - tests/test_notion_scrum_preflight.py
decisions:
  - Delegated all people-state validation rules to validate_people_state(data, registry=registry) — no re-implementation
  - Schema-version check is an explicit gate before delegation (D-17)
  - Missing file with require_people_state=False is a warning; True is an error (D-16)
  - All staffing additions go into data sub-fields; result envelope shape unchanged
  - Fixed _write_empty_prompts fixture: wrote bare list "[]" instead of dict container
metrics:
  duration_minutes: 5
  completed_date: "2026-04-24"
---

# Phase 13 Plan 03: Preflight Staffing Extension Summary

## Summary

Extended `run_preflight` additively with two new keyword args (`people_state_path`, `require_people_state`) and an additive staffing-integrity check block that validates `people_state.json` after all existing registry/prompt checks — without changing the result envelope shape or breaking any existing callers.

**One-liner:** `run_preflight` extended with optional people-state integrity gate delegating to `validate_people_state` with registry cross-check.

## Files Modified

| File | Change |
|------|--------|
| `scripts/notion_scrum/preflight.py` | Added `people_state_path` + `require_people_state` params, staffing check block, `DEFAULT_PEOPLE_STATE` constant, `people_state_store` import, CLI args |
| `tests/test_notion_scrum_preflight.py` | Fixed `_write_empty_prompts` fixture to write proper dict container instead of bare list |

## New run_preflight Signature

```python
def run_preflight(
    *,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
    people_state_path: Path | None = None,        # NEW (PRE-01..04)
    require_people_state: bool = False,           # NEW (PRE-01)
) -> dict:
```

## Staffing Check Insertion Point

Lines 55-76 of `scripts/notion_scrum/preflight.py` (immediately after the prompt validation loop, before `append_event`):

```
# --- Staffing integrity checks (additive, per D-19) ---
if people_state_path is not None:
    if not people_state_path.exists():
        [warning or error based on require_people_state]
    else:
        [load → schema_version gate → validate_people_state delegation]
```

## Test Results

### PRE Preflight Tests (Plan 03 target)

```
tests/test_notion_scrum_preflight.py — 7 passed
```

All 7 PRE test functions GREEN:
- `test_preflight_missing_people_state_is_warning` — ok=True, warning in data["warnings"]
- `test_preflight_invalid_people_state_version_is_error` — ok=False, schema_version error
- `test_preflight_malformed_people_state_json_is_error` — ok=False, parse error
- `test_preflight_unknown_backup_key_is_error` — ok=False, backup error via validate_people_state
- `test_preflight_invalid_leave_dates_is_error` — ok=False, leave window error via validate_people_state
- `test_preflight_legacy_registry_and_prompt_checks_still_run` — ok=True, RESULT_KEYS preserved
- `test_preflight_success_preserves_stable_envelope_with_staffing` — ok=True, envelope intact

### Existing Tests (no regression)

```
tests/test_notion_scrum.py — 30 passed
tests/test_notion_scrum_people_state.py — 7 passed (from baseline)
Total: 37 passed, 0 failed
```

### Staffing Snapshot Tests (Plan 02 scope, still RED)

`tests/test_notion_scrum_staffing_snapshot.py` remains RED with `ModuleNotFoundError: No module named 'build_staffing_snapshot'` — expected; Plan 02 (parallel wave) implements that module.

## Validation: No Re-implementation of People-State Rules

```bash
grep -n "since\|until\|backup" scripts/notion_scrum/preflight.py | grep -v "import\|#"
```

Result: Only `validate_people_state` delegation line — no raw date comparison or backup-key lookup re-implemented in `preflight.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _write_empty_prompts fixture writing bare list**

- **Found during:** Task 1 (first test run)
- **Issue:** `_write_empty_prompts` in `tests/test_notion_scrum_preflight.py` wrote `"[]"` (bare JSON list), but `prompt_store.load_prompts` expects a dict container with a `"prompts"` key. All 7 preflight tests failed with `AttributeError: 'list' object has no attribute 'get'`.
- **Fix:** Changed `_write_empty_prompts` to write `{"schema_version": "1.0", "updated_at": "...", "prompts": []}` matching the format existing tests use (e.g., `test_notion_scrum.py` line 685).
- **Files modified:** `tests/test_notion_scrum_preflight.py`
- **Commit:** d1cadec

## Key Decisions

1. **No re-implementation of validation rules:** `preflight.py` delegates entirely to `validate_people_state(data, registry=registry)` from `people_state_store`. Only the schema-version pre-gate is in `preflight.py`.
2. **Explicit file-existence check:** `people_state_path.exists()` is called explicitly (not relying on `load_people_state`'s missing-file default) to distinguish missing-file warning from present-but-empty-valid file.
3. **Result envelope unchanged:** `people_state_checked` added inside `data` sub-dict; no new top-level result keys. `set(result.keys()) == set(RESULT_KEYS)` preserved.
4. **Fixture bug fix:** The `_write_empty_prompts` in the RED test file used an incorrect format. Fixed as part of GREEN implementation (Rule 1 auto-fix).

## Known Stubs

None — all behaviors fully implemented and tested.

## Threat Flags

None — all threat register mitigations from plan's `<threat_model>` implemented:
- T-13-03-01: Schema-version check gate before validation
- T-13-03-02: validate_people_state with registry= kwarg catches unknown backup keys
- T-13-03-03: JSONDecodeError and ValueError caught explicitly
- T-13-03-04: All staffing additions in data sub-fields; RESULT_KEYS enforced
- T-13-03-05: No bare except clauses; specific exception types only
- T-13-03-06: Accepted (operator-only CLI, OS permissions apply)

## Self-Check

### Files exist

- `scripts/notion_scrum/preflight.py` — modified, exists
- `tests/test_notion_scrum_preflight.py` — modified (fixture fix), exists

### Commits exist

- `d1cadec` — feat(13-03): extend preflight with additive staffing integrity checks

## Self-Check: PASSED
