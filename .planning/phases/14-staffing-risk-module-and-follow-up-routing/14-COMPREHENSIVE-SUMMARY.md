---
phase: 14-staffing-risk-module-and-follow-up-routing
plan: comprehensive
subsystem: api
tags: [staffing-risk, follow-up-routing, tdd, pytest, python, policy-layer]

requires:
  - phase: 13
    provides: staffing_snapshot.json structure, project_effective_owners, risk_flags pre-computation
  - phase: 11
    provides: people_state_store.py with effective_followup_target() and is_person_absent()

provides:
  - scripts/notion_scrum/staffing_risk.py — importable policy module with detect_risks() and compute_routing_recommendation()
  - tests/test_notion_scrum_staffing_risk.py — 10 named tests covering all 9 requirements (RISK-01..05, ROUT-01..04)
  - Stable risk detection and routing contracts for Phase 15 consumption

affects:
  - 15-daily-board-report-staffing-sections
  - Any downstream phase consuming staffing risk output or routing recommendations

tech-stack:
  added: []
  patterns:
    - "TDD RED → GREEN: test contract before implementation enforces correctness"
    - "Inline helper builder pattern (no @pytest.fixture) — matches existing test_notion_scrum_staffing_snapshot.py style"
    - "sys.path.insert with ROOT/scripts/notion_scrum for module isolation in tests"
    - "people_state_store routing fallback: people_state-aware when provided, snapshot-only fallback when None"
    - "Stable sort on all risk lists (person_key / task_id / project_id) for deterministic JSON"

key-files:
  created:
    - scripts/notion_scrum/staffing_risk.py
    - tests/test_notion_scrum_staffing_risk.py
  modified: []

key-decisions:
  - "D-01/D-02: Single staffing_risk.py module with two primary exports (detect_risks, compute_routing_recommendation) — clean policy layer separation from Phase 13 snapshot derivation"
  - "D-05: Overridable thresholds (overload_projects_threshold=3, overload_tasks_threshold=8) — matches PRD §12.2 and enables test flexibility"
  - "D-15: recommendation_only: True always — routing recommends, never auto-mutates Notion ownership"
  - "D-17: Optional people_state param — snapshot-only and people_state-aware workflows both supported"
  - "RISK-02: Project title resolved by index lookup in person active_project_ids/active_project_titles — project_effective_owners has no title field"
  - "RISK-04: Overload check is pure count threshold — no availability_status or risk_flags check"
  - "TDD RED: tests assert on expected return dict structure (not pytest.raises) — all 10 show as FAILED in RED phase, PASSED in GREEN"

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

duration: 4min
completed: 2026-04-24
---

# Phase 14 Comprehensive Summary: Staffing Risk Module and Follow-Up Routing

**TDD RED + GREEN implementation of staffing_risk.py policy module with detect_risks() for 5 risk categories and compute_routing_recommendation() for 4 routing paths — all 10 tests pass, 191+ test suite green, stable contracts established for Phase 15**

## Performance

- **Duration:** 4 min total (2 plans x 2 min each)
- **Plans completed:** 2 (14-01 TDD RED, 14-02 TDD GREEN)
- **Tasks completed:** 4
- **Files created:** 2
- **Files modified:** 0 (additive-only phase)

## Phase Objective

Enable the system to:
1. Identify all staffing risks from a pre-built snapshot without re-deriving facts
2. Route follow-up decisions that account for owner availability, backup assignment, and bandwidth constraints
3. Surface routing recommendations as non-mutating metadata for downstream consumers
4. Maintain separation of concerns: snapshot = facts (Phase 13), staffing_risk = policy (Phase 14)

## Accomplishments

### Plan 14-01: TDD RED Phase

- Created importable `staffing_risk.py` stub with `detect_risks` and `compute_routing_recommendation` raising `NotImplementedError`
- Created `tests/test_notion_scrum_staffing_risk.py` with 10 named test functions (RISK-01..05, ROUT-01..04 + threshold override)
- All 10 tests FAILED (not collection errors) — RED phase contract established
- No regressions: 181 existing non-integration tests pass

### Plan 14-02: TDD GREEN Phase

- Implemented `detect_risks()` covering all 5 risk categories with stable sorting:
  - RISK-01: Absent owner tasks (reads `absent_owner` risk_flag, zips task IDs + titles)
  - RISK-02: Absent owner projects (resolves project title by index lookup in person's active_project_titles)
  - RISK-03: Absent no backup (reads `absent_no_backup` risk_flag)
  - RISK-04: Overloaded owners (pure count threshold — no availability_status check)
  - RISK-05: Reduced bandwidth with overdue tasks (`bandwidth in {reduced, limited}` AND `overdue_tasks > 0`)
- Implemented `compute_routing_recommendation()` with people_state-aware routing and snapshot fallback:
  - ROUT-01: Active owner → return owner as routing target (`owner_active`)
  - ROUT-02: Absent owner + backup → return backup as target (`owner_absent_backup_used`)
  - ROUT-03: Absent owner + no backup → return escalation signal (`escalation_needed`)
  - ROUT-04: All routing paths return `recommendation_only: True`
- Bandwidth note appended when `bandwidth in {reduced, limited}`
- All 10 tests PASS; no regressions in 191-test suite

## Task Commits

All work committed atomically per task:

| Plan | Task | Commit | Type | Description |
|------|------|--------|------|-------------|
| 14-01 | T1 | `344cba2` | test | Add staffing_risk.py stub with NotImplementedError signatures |
| 14-01 | T2 | `278bb54` | test | Add failing test suite for staffing risk module (RED phase) |
| 14-02 | T1+T2 | `f7abf82` | feat | Implement detect_risks and compute_routing_recommendation GREEN phase |
| Metadata | - | `4d3e348` | docs | Complete staffing-risk GREEN phase plan |
| Metadata | - | `5473160` | docs | Complete phase execution (STATE.md, ROADMAP.md) |

## Files Created

- **`scripts/notion_scrum/staffing_risk.py`** (166 lines)
  - `detect_risks(snapshot, overload_projects_threshold=3, overload_tasks_threshold=8)` — detects all 5 risk categories, returns structured dict with schema_version, generated_at, thresholds, risks
  - `compute_routing_recommendation(snapshot_person, people_state=None)` — derives routing target with recommendation_only enforcement and bandwidth notes
  - Imports: `people_state_store`, `common.utc_now_iso`
  - No circular imports; pure functions; no I/O

- **`tests/test_notion_scrum_staffing_risk.py`** (330+ lines)
  - 10 named test functions: `test_risk_01_absent_owner_tasks`, `test_risk_02_absent_owner_projects`, `test_risk_03_absent_no_backup`, `test_risk_04_overloaded_owners`, `test_risk_04_threshold_override`, `test_risk_05_reduced_bandwidth_overdue`, `test_rout_01_active_owner`, `test_rout_02_backup_routing`, `test_rout_03_escalation_needed`, `test_rout_04_recommendation_only`
  - 4 inline helper builders: `_snapshot_with_absent_owner_task`, `_snapshot_with_overloaded_person`, `_snapshot_with_reduced_bandwidth`, `_snapshot_person_dict`
  - Zero fixtures, zero I/O, pure inline dicts

## Requirement Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| RISK-01 | Tasks assigned to absent owners are identified | Complete |
| RISK-02 | Projects whose owners are on leave (no effective substitute) identified | Complete |
| RISK-03 | Absent owners with no backup configured are flagged | Complete |
| RISK-04 | Overloaded owners (>=3 projects or >=8 tasks) identified regardless of availability | Complete |
| RISK-05 | Reduced-bandwidth owners carrying overdue work are flagged | Complete |
| ROUT-01 | Active owner → return owner as routing target (owner_active) | Complete |
| ROUT-02 | Absent owner + backup → return backup as target (owner_absent_backup_used) | Complete |
| ROUT-03 | Absent owner + no backup → return escalation signal (escalation_needed) | Complete |
| ROUT-04 | All routing paths return recommendation_only: True (no Notion mutation) | Complete |

## Stable Contracts for Phase 15

### Risk Detection Output (detect_risks)

```python
{
    "schema_version": "1.0",
    "generated_at": "<ISO timestamp>",
    "thresholds": {"overload_projects": 3, "overload_tasks": 8},
    "risks": {
        "absent_owner_tasks": [{"task_id", "task_title", "owner_key", "backup_key"}],
        "absent_owner_projects": [{"project_id", "project_title", "owner_key", "backup_key"}],
        "absent_no_backup": [{"person_key", "display_name", "active_projects", "active_tasks"}],
        "overloaded_owners": [{"person_key", "display_name", "active_projects", "active_tasks"}],
        "reduced_bandwidth_with_overdue": [{"person_key", "display_name", "overdue_tasks", "bandwidth"}],
    }
}
```

### Routing Recommendation Output (compute_routing_recommendation)

```python
{
    "target_person_key": str,
    "routing_reason": str,  # one of: owner_active, owner_absent_backup_used, escalation_needed, unknown
    "recommendation_only": True,  # always True
    "note": str | None,  # non-None when bandwidth is reduced/limited
}
```

## Deviations from Plan

None — both plans executed exactly as written.

## Issues Encountered

None — no bugs, blockers, or unexpected dependencies.

## Known Stubs

None — staffing_risk.py is fully implemented. No placeholder values, no TODO comments, no hardcoded empty returns.

## Threat Flags

None — staffing_risk.py is a pure computation module with no network endpoints, no file I/O, no auth paths, and no schema changes at trust boundaries.

## Self-Check

- `scripts/notion_scrum/staffing_risk.py` — EXISTS (verified)
- `tests/test_notion_scrum_staffing_risk.py` — EXISTS (verified)
- All 10 staffing risk tests — PASS (verified: `10 passed in 0.02s`)
- Full regression suite — PASS (verified: `196 passed in 62.38s`)
- Import check — PASS (no circular imports)
- Commit `344cba2` — EXISTS (git log verified)
- Commit `278bb54` — EXISTS (git log verified)
- Commit `f7abf82` — EXISTS (git log verified)

## Self-Check: PASSED

## Phase 15 Handoff

Phase 15 (Daily Board Report Staffing Sections) should:
1. Read `staffing_risk.py` docstrings for function contracts
2. Read 14-CONTEXT.md D-XX decisions for design intent
3. Read `test_notion_scrum_staffing_risk.py` for expected return shapes
4. Import `detect_risks()` to generate risk lists for staffing report sections
5. Import `compute_routing_recommendation()` to derive action line text
6. Confirm `backup_person_key` resolution matches routing logic

---
*Phase: 14-staffing-risk-module-and-follow-up-routing*
*Completed: 2026-04-24*
*Summary written: 2026-04-29*
