---
phase: 11-people-state-schema-store-and-contracts
verified: 2026-04-24T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 11: People-State Schema, Store, and Contracts — Verification Report

**Phase Goal:** Operators and the system share one validated, versioned people_state.json contract and a centralized store module so all later scripts build on a stable foundation.
**Verified:** 2026-04-24
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | `people_state.json` can be loaded, saved, and schema-validated; invalid enum values, date inversions, and unknown backup keys are rejected | VERIFIED | All 5 validation tests pass: `test_validate_rejects_invalid_status`, `test_validate_rejects_invalid_bandwidth`, `test_validate_rejects_invalid_date_window`, `test_validate_rejects_unknown_backup_key`, `test_load_save_valid_container` |
| SC2 | All four store transitions (`set_leave`, `clear_leave`, `set_bandwidth`, `set_backup`) apply correctly and deterministically | VERIFIED | `test_set_leave_transition`, `test_clear_leave_transition`, `test_set_bandwidth_transition`, `test_set_backup_transition` all pass; transition functions are pure — modify in-place and return data |
| SC3 | `is_person_absent` and `effective_followup_target` return correct results for active, leave, ooo, and unknown availability states | VERIFIED | 5 tests pass covering all four routing cases: active→`owner_active`, leave+backup→`owner_absent_backup_used`, leave+no-backup→`escalation_needed`, missing→`unknown`; ooo treated same as leave |
| SC4 | Result envelopes include `effective_followup_person_key` and `routing_reason` fields | VERIFIED | `result_contracts.RESULT_KEYS` has 14 entries; `build_result()` default returns `effective_followup_person_key=None`, `routing_reason="unknown"`; `test_result_envelope_includes_staffing_fields` passes |
| SC5 | Missing `people_state.json` is treated as `unknown` availability on all read paths without raising an error | VERIFIED | `load_people_state` uses `load_json(..., default={...})` pattern; `test_load_missing_file_returns_empty_container` passes; `is_person_absent` returns `False` for missing person; `effective_followup_target` returns `(key, "unknown")` for missing person |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_notion_scrum_people_state.py` | Failing test suite covering all Phase 11 requirements | VERIFIED | 16 test functions, imports `people_state_store` and `result_contracts` via `sys.path.insert`, inline helper pattern (no conftest.py), `tmp_path` used in 11 locations |
| `scripts/notion_scrum/people_state_store.py` | Complete people state store module | VERIFIED | 218 lines, 11 functions (1 private `_ensure_person` + 10 public), `VALID_STATUSES` and `VALID_BANDWIDTHS` frozensets, pure transition functions, no third-party imports |
| `scripts/notion_scrum/result_contracts.py` | Extended result envelope with staffing fields | VERIFIED | 14 RESULT_KEYS (up from 12), `effective_followup_person_key: str | None = None` and `routing_reason: str = "unknown"` in `build_result` signature and return dict; `merge_result` unchanged |
| `state/notion_scrum/people_state.json` | Bootstrap empty-container people state file | VERIFIED | Exact content `{"schema_version": "1.0", "updated_at": "2026-04-24T00:00:00Z", "people": {}}`, not gitignored |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_notion_scrum_people_state.py` | `scripts/notion_scrum/people_state_store` | `sys.path.insert + import people_state_store` | WIRED | Line 12-14: `sys.path.insert` + `import people_state_store`; all 15 store-module test functions call module functions directly |
| `tests/test_notion_scrum_people_state.py` | `scripts/notion_scrum/result_contracts` | `import result_contracts` | WIRED | Line 15: `import result_contracts`; `test_result_envelope_includes_staffing_fields` accesses `RESULT_KEYS` and `build_result()` |
| `scripts/notion_scrum/people_state_store.py` | `scripts/notion_scrum/common.py` | `from common import load_json, save_json, utc_now_iso` | WIRED | Line 8; all three are used: `load_json` in `load_people_state`, `save_json` in `save_people_state`, `utc_now_iso` in all transition functions |
| `scripts/notion_scrum/people_state_store.py` | `state/notion_scrum/people_state.json` | `load_people_state / save_people_state using load_json / save_json` | WIRED | Path is passed by caller; store module delegates to `common.py` for atomic read/write; `people_state.json` is the operational file consumed |
| `result_contracts.RESULT_KEYS` | `build_result` signature | keyword-only args with defaults matching key names | WIRED | `effective_followup_person_key` and `routing_reason` appear in `RESULT_KEYS` tuple, `build_result` signature, and return dict — 3 occurrences each; `merge_result` picks them up automatically via `for key in RESULT_KEYS` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `people_state_store.py::load_people_state` | return value | `common.load_json` with `default=` empty container | Yes — reads from filesystem; default only on missing file | FLOWING |
| `people_state_store.py::validate_people_state` | `errors: list[str]` | iterates `data.get("people", {}).items()`, applies enum checks and `date.fromisoformat()` | Yes — derives from actual input data | FLOWING |
| `people_state_store.py::effective_followup_target` | `(target_key, routing_reason)` tuple | reads `person.get("availability", {}).get("status")` and `backup_person_key` from data | Yes — derives from actual person record fields | FLOWING |
| `result_contracts.py::build_result` | `routing_reason`, `effective_followup_person_key` | keyword args passed by caller; defaults `"unknown"` / `None` | Yes — real defaults, not hollow; callers populate when routing is known | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 16 Phase 11 tests pass | `python3 -m pytest tests/test_notion_scrum_people_state.py -v` | 16 passed in 0.02s | PASS |
| No regressions in full suite | `PYTHONPATH=src python3 -m pytest tests/ -x -q` | 152 passed | PASS |
| `result_contracts` has 14 keys with correct defaults | `python3 -c "import result_contracts; assert len(RESULT_KEYS)==14"` | keys: 14, routing_reason: unknown, efk: None | PASS |
| Missing file returns empty container (not raise) | `load_people_state(path / "nonexistent.json")` | `people == {}`, `schema_version` present, no exception | PASS |
| All four routing cases correct | spot-check via python3 | missing→`unknown`, active→`owner_active`, leave+backup→`owner_absent_backup_used`, leave+no-backup→`escalation_needed` | PASS |
| `people_state.json` exact bootstrap shape | `python3 -c "json.load(...) == {'schema_version':'1.0', ...}"` | `True` | PASS |
| No third-party imports in store module | `grep -E "import pydantic|import requests"` | NO THIRD-PARTY IMPORTS FOUND | PASS |
| Store module has 11 functions | `grep -c "^def " people_state_store.py` | 11 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| STATE-01 | 11-01, 11-02 | Load and save valid `people_state.json` | SATISFIED | `load_people_state` / `save_people_state` implemented; `test_load_save_valid_container` passes |
| STATE-02 | 11-01, 11-02 | Validates `availability.status` enum | SATISFIED | `VALID_STATUSES` frozenset check in `validate_people_state`; `test_validate_rejects_invalid_status` passes |
| STATE-03 | 11-01, 11-02 | Validates `capacity.bandwidth` enum | SATISFIED | `VALID_BANDWIDTHS` frozenset check in `validate_people_state`; `test_validate_rejects_invalid_bandwidth` passes |
| STATE-04 | 11-01, 11-02 | Rejects leave date windows where `until < since` | SATISFIED | `date.fromisoformat()` comparison in `validate_people_state`; `test_validate_rejects_invalid_date_window` passes |
| STATE-05 | 11-01, 11-02 | Rejects backup keys not in `team_registry.json` | SATISFIED | Registry lookup in `validate_people_state`; `test_validate_rejects_unknown_backup_key` passes |
| STATE-06 | 11-01, 11-02 | `set_leave` transition applies correctly | SATISFIED | `set_leave` sets status/since/until/backup_person_key/note/source/updated_at; `test_set_leave_transition` passes |
| STATE-07 | 11-01, 11-02 | `clear_leave` transition resets to active | SATISFIED | `clear_leave` sets status=active, clears since/until/note; `test_clear_leave_transition` passes |
| STATE-08 | 11-01, 11-02 | `set_bandwidth` and `set_backup` transitions | SATISFIED | Both implemented; `test_set_bandwidth_transition` and `test_set_backup_transition` pass |
| STATE-09 | 11-01, 11-02 | `is_person_absent` and `effective_followup_target` | SATISFIED | Both implemented with correct semantics; 5 tests cover all routing cases |
| STATE-10 | 11-01, 11-02, 11-03 | Result envelopes include staffing fields | SATISFIED | `result_contracts.RESULT_KEYS` has 14 keys; `build_result()` defaults correct; `test_result_envelope_includes_staffing_fields` passes |
| COMPAT-02 | 11-01, 11-02 | Missing `people_state.json` returns graceful empty state | SATISFIED | `load_people_state` uses `load_json(default=...)` pattern; `is_person_absent` returns False for missing person; `effective_followup_target` returns `(key, "unknown")` for missing person |

**Note on DOCS-01:** The CONTEXT.md for Phase 11 listed a schema reference doc (`docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md`) as part of Phase 11 scope, but REQUIREMENTS.md maps `DOCS-01` to **Phase 16**. The file exists at `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md`. This is not a gap — the ROADMAP Phase 11 success criteria do not include it, and the requirement is formally assigned to Phase 16.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODOs, FIXMEs, placeholder returns, hardcoded empty values flowing to renderers, or stub implementations found in any Phase 11 artifact.

---

### Human Verification Required

None. All must-haves are programmatically verifiable and verified.

---

### Gaps Summary

No gaps. All five ROADMAP success criteria are met. All 11 requirements (STATE-01 through STATE-10 and COMPAT-02) are satisfied by passing tests. The full 152-test suite passes with no regressions.

**Phase 11 goal is achieved.** The codebase now has:
- A validated, versioned `people_state.json` contract with bootstrap file
- A centralized `people_state_store.py` module with 10 public functions and deterministic pure transitions
- Extended `result_contracts.py` with staffing routing fields (14 keys total)
- A green TDD test suite of 16 tests as the living contract for Phase 12+ consumers

---

_Verified: 2026-04-24_
_Verifier: Claude (gsd-verifier)_
