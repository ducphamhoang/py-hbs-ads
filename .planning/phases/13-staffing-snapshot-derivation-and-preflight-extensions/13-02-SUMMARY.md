---
phase: 13-staffing-snapshot-derivation-and-preflight-extensions
plan: "02"
subsystem: staffing-snapshot-derivation
tags:
  - tdd
  - green-state
  - staffing-snapshot
  - read-optimized
  - local-derivation

requires:
  - phase: 13-01
    provides: "RED test suite (11 tests) locking snapshot builder contract (SNAP-01..04)"
  - phase: 11-people-state-schema-store-and-contracts
    provides: "people_state_store module with is_person_absent, effective_followup_target, load_people_state"
  - phase: 12-operator-cli-write-and-query-surface
    provides: "board_cache.load_snapshot, common.load_registry, save_json, utc_now_iso"

provides:
  - "build_staffing_snapshot.build_staffing_snapshot() — importable derivation function"
  - "build_staffing_snapshot.write_staffing_snapshot() — atomic file write via save_json"
  - "build_staffing_snapshot.main() — thin CLI entrypoint with --dry-run"
  - "staffing_snapshot.json derived artifact schema: schema_version, generated_at, inputs, meta, people, project_effective_owners"
  - "11 snapshot tests GREEN (SNAP-01..SNAP-04)"

affects:
  - "Phase 13-03 (preflight extension — builds on same module patterns)"
  - "Phase 14 (risk module — consumes person counts and risk_flags)"
  - "Phase 15 (daily report — consumes staffing_snapshot.json)"

tech-stack:
  added:
    - "build_staffing_snapshot.py module (290 lines)"
  patterns:
    - "Board cache + registry join for assignment resolution (D-02: people_state cannot inject assignments)"
    - "_INACTIVE_STATUSES frozenset vocabulary lock pattern"
    - "Unresolved Notion owner IDs preserved in meta.unresolved_owner_ids (D-12)"
    - "Per-person risk_flags as low-level derived facts (D-09: no threshold enforcement at this phase)"
    - "project_effective_owners via effective_followup_target() substitution"
    - "Local CLI with --dry-run and compact JSON stdout following query_people_state.py pattern"

key-files:
  created:
    - scripts/notion_scrum/build_staffing_snapshot.py
  modified: []

key-decisions:
  - "_INACTIVE_STATUSES = frozenset({'Done', 'Archived'}) — active = NOT in this set"
  - "Assignments derive exclusively from board cache owner_ids + registry notion.user_id join (D-02)"
  - "Unresolved owner IDs preserved in snapshot['meta']['unresolved_owner_ids'], never silently dropped (D-12)"
  - "Risk flags at Phase 13: absent_owner, absent_no_backup — no Phase 14 thresholds applied"
  - "display_name prefers registry.notion.display_name, falls back to top-level display_name, then canonical key (D-07)"
  - "project_effective_owners sorted for stable JSON output"

patterns-established:
  - "Staffing derivation pipeline: registry index → resolve owners → initialize accumulators → walk projects → walk tasks → compute risk flags → build effective owners → assemble result"
  - "Blocked task detection: blocked_reason non-empty OR status=='Blocked' (union, not exclusive)"
  - "Overdue task detection: active task with due_date < today_iso (string comparison, ISO dates)"
  - "Undated task detection: active task with due_date is None"

requirements-completed:
  - SNAP-01
  - SNAP-02
  - SNAP-03
  - SNAP-04

duration: 8min
completed: "2026-04-24"
---

# Phase 13 Plan 02: Staffing Snapshot Builder (GREEN) Summary

**Local read-optimized staffing snapshot builder deriving per-person workload, availability, and effective-owner substitution from registry + board cache + people_state without any Notion API calls**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-24T15:21:00Z
- **Completed:** 2026-04-24T15:29:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented `scripts/notion_scrum/build_staffing_snapshot.py` (290 lines) with all required exports: `build_staffing_snapshot`, `write_staffing_snapshot`, `main`
- Turned all 11 RED snapshot tests GREEN (SNAP-01..04 contract fully satisfied)
- Full regression maintained: 67 tests pass (56 prior + 11 new snapshot tests)
- No live Notion API calls anywhere in the module — fully local, deterministic, network-free

## Function Signatures as Implemented

```python
def build_staffing_snapshot(
    registry: dict[str, Any],
    people_state: dict[str, Any],
    board_snapshot: dict[str, Any],
    today_iso: str | None = None,
) -> dict[str, Any]: ...

def write_staffing_snapshot(path: Path, snapshot: dict[str, Any]) -> None: ...

def main() -> None: ...  # --registry, --people-state, --board-cache, --output, --dry-run
```

## Active-Status Vocabulary (Locked in _INACTIVE_STATUSES)

```python
_INACTIVE_STATUSES: frozenset[str] = frozenset({"Done", "Archived"})
# Active = NOT IN _INACTIVE_STATUSES → includes "Not started", "In progress"
# Blocked: blocked_reason non-empty OR status == "Blocked" (union)
# Overdue: active task with due_date < today_iso
# Undated: active task with due_date is None
```

## Risk Flags Implemented (Phase 13, D-09)

- `"absent_owner"` — person's availability.status is "leave" or "ooo"
- `"absent_no_backup"` — absent person has no backup_person_key

Phase 14 workload thresholds (>=3 projects, >=8 tasks) are deliberately NOT applied here.

## Task Commits

1. **Task 1: Implement build_staffing_snapshot module (GREEN)** - `46ca23c` (feat)

## Files Created/Modified

- `scripts/notion_scrum/build_staffing_snapshot.py` — Importable derivation function + atomic file writer + thin CLI entrypoint (290 lines)

## Decisions Made

1. **Active-status vocabulary:** `_INACTIVE_STATUSES = frozenset({"Done", "Archived"})` — locked as module constant matching test assertions
2. **Display name preference:** `registry.notion.display_name` > `registry.display_name` > `canonical_person_key` — handles person2's `None` notion display_name gracefully
3. **Sorted outputs:** All list outputs (project_ids, task_ids, unresolved_ids, effective_owner_keys, board_owner_keys) are sorted for stable JSON — consistent with D-14
4. **Blocked detection union:** `bool(blocked_reason) OR status == "Blocked"` — matches test fixture (task-3 has blocked_reason "Waiting on feedback", status "In progress")
5. **project_effective_owners scope:** Only built for active projects (not in _INACTIVE_STATUSES) — project-2 "Beta" (status="Done") excluded

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Implementation passed all 11 tests on first run with no iteration needed.

## Known Stubs

None. All fields fully implemented and wired from live data sources.

## Threat Flags

No new network surfaces introduced. Module is local-only. All mitigations from the plan's STRIDE threat register are implemented:

- **T-13-02-01:** Assignments derive from board cache + registry join only — people_state consulted for availability/backup only
- **T-13-02-02:** Owner IDs treated as string dict keys only — no shell execution
- **T-13-02-03:** CLI path only accessible by operators; save_json uses atomic tmp write
- **T-13-02-06:** Exact-match lookup only in notion_id_to_person_key — no fuzzy fallback

## Confirmation

- All 11 snapshot tests GREEN: `python3 -m pytest tests/test_notion_scrum_staffing_snapshot.py -q` → `11 passed`
- No live API imports: `grep -n "notion_request|load_api_key" build_staffing_snapshot.py` → empty
- Full regression: `67 passed` (56 prior + 11 new snapshot tests)

## Next Phase Readiness

- **Plan 13-03:** Extend `scripts/notion_scrum/preflight.py` with `people_state_path` and `require_people_state` kwargs → turns 7 preflight RED tests GREEN
- **Phase 14:** Risk module can consume `snapshot["people"][key]["active_projects"]`, `["active_tasks"]`, and `["risk_flags"]` directly from the stable schema

## Self-Check: PASSED

- `scripts/notion_scrum/build_staffing_snapshot.py` exists: FOUND
- Commit `46ca23c` exists: FOUND
- 11 tests pass: CONFIRMED
- No live API imports: CONFIRMED

---
*Phase: 13-staffing-snapshot-derivation-and-preflight-extensions*
*Completed: 2026-04-24*
