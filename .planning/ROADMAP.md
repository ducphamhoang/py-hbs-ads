# Roadmap: py-hbs-ads

## Milestones

- ✅ **v1.0 Python rewrite foundation** — Phases 1-6 shipped before the current GSD cycle; full history preserved in [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md).
- ✅ **v2.0 Hermes Discord ↔ Notion Scrum Level 2+3** — Phases 8-10 shipped 2026-04-22; archived in [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md).
- 🚧 **v3.0 Staffing-Aware Discord↔Notion Scrum** — Phases 11-16 (in progress)

## Current Planning State

### 🚧 v3.0 Staffing-Aware Discord↔Notion Scrum

**Milestone goal:** Add a people-state layer so Hermes can track leave/availability, derive assignment risk, and produce staffing-aware follow-ups and reports without weakening guarded-write safety.

## Phases

- [ ] **Phase 11: People-State Schema, Store, and Contracts** - Define the staffing data model, implement the shared store module, bootstrap the state file, extend result contracts, and establish test coverage.
- [ ] **Phase 12: Operator CLI Write and Query Surface** - Build the guarded `update_people_state.py` write path and the read-only `query_people_state.py` query surface.
- [ ] **Phase 13: Staffing Snapshot Derivation and Preflight Extensions** - Implement `build_staffing_snapshot.py` to derive the merged snapshot and extend preflight with people-state integrity checks.
- [x] **Phase 14: Staffing Risk Module and Follow-Up Routing** - Implement staffing risk detection and the effective follow-up routing helpers. (completed 2026-04-24)
- [ ] **Phase 15: Daily Board Report Staffing Sections and Backward-Compat Guard** - Extend the daily board report with staffing-aware output while preserving board-only fallback.
- [ ] **Phase 16: Skill and Documentation Updates** - Update the Hermes skill and supporting docs to explain the three-layer state model.

## Phase Details

### Phase 11: People-State Schema, Store, and Contracts
**Goal**: Operators and the system share one validated, versioned `people_state.json` contract and a centralized store module so all later scripts build on a stable foundation.
**Depends on**: Phase 10 (v2.0 shared modules in place)
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04, STATE-05, STATE-06, STATE-07, STATE-08, STATE-09, STATE-10, COMPAT-02
**Success Criteria** (what must be TRUE):
  1. `people_state.json` can be loaded, saved, and schema-validated; invalid enum values, date inversions, and unknown backup keys are rejected.
  2. All four store transitions (`set_leave`, `clear_leave`, `set_bandwidth`, `set_backup`) apply correctly and deterministically to a person record.
  3. `is_person_absent` and `effective_followup_target` return correct results for active, leave, ooo, and unknown availability states.
  4. Result envelopes produced by store helpers include `effective_followup_person_key` and `routing_reason` fields.
  5. Missing `people_state.json` is treated as `unknown` availability on all read paths without raising an error.
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md — Failing test suite (RED phase): all 11 requirements covered by named test functions
- [x] 11-02-PLAN.md — people_state_store.py implementation (GREEN phase): load/save/validate/transitions/queries
- [x] 11-03-PLAN.md — result_contracts.py extension + bootstrap people_state.json

### Phase 12: Operator CLI Write and Query Surface
**Goal**: Operators can update staffing state through a guarded, dry-run-first CLI and inspect it through a read-only query tool without touching JSON files directly.
**Depends on**: Phase 11
**Requirements**: SCLI-01, SCLI-02, SCLI-03, SCLI-04, SCLI-05
**Success Criteria** (what must be TRUE):
  1. `update_people_state.py` accepts structured flags (`--person`, `--action`, `--until`, `--bandwidth`, `--backup`, `--note`) and outputs a dry-run description of the intended change by default.
  2. `update_people_state.py` writes state only when `--execute` is supplied; all other invocations are non-mutating.
  3. `update_people_state.py` stops and surfaces an explicit ambiguity error when a person alias maps to multiple registry candidates.
  4. `query_people_state.py` returns correct results for `--person`, `--on-leave-today`, `--reduced-bandwidth`, and `--backup-for` modes without requiring any preflight.
**Plans**: TBD

### Phase 13: Staffing Snapshot Derivation and Preflight Extensions
**Goal**: The system can build a merged, read-optimized `staffing_snapshot.json` from registry, board cache, and people state, and preflight validates people-state integrity before live operations depend on it.
**Depends on**: Phase 12
**Requirements**: SNAP-01, SNAP-02, SNAP-03, SNAP-04, PRE-01, PRE-02, PRE-03, PRE-04
**Success Criteria** (what must be TRUE):
  1. `build_staffing_snapshot.py` generates `cache/staffing_snapshot.json` containing per-person display name, availability status, leave window, backup key, active project/task IDs and titles, counts, and risk flags.
  2. Project and task assignments in the snapshot are derived from board cache owner IDs and registry Notion mappings — not from manually entered fields in `people_state.json`.
  3. Snapshot includes a `project_effective_owners` map that reflects leave/backup substitution for each project.
  4. Preflight warns (not errors) when `people_state.json` is absent for read-only workflows, and errors when an existing file has an invalid schema or unsupported version for staffing-aware write operations.
  5. Preflight validates that all backup person keys exist in `team_registry.json` and that all leave date windows are logically valid.
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — Failing test suite (RED phase): snapshot contract (SNAP-01..04) and preflight staffing extension (PRE-01..04)
- [x] 13-02-PLAN.md — build_staffing_snapshot.py implementation: local derivation module + thin CLI
- [x] 13-03-PLAN.md — preflight.py additive staffing integrity extension

### Phase 14: Staffing Risk Module and Follow-Up Routing
**Goal**: The system can detect all five staffing risk categories and compute the correct effective follow-up target for any owner availability state without modifying Notion ownership.
**Depends on**: Phase 13
**Requirements**: RISK-01, RISK-02, RISK-03, RISK-04, RISK-05, ROUT-01, ROUT-02, ROUT-03, ROUT-04
**Success Criteria** (what must be TRUE):
  1. The risk module identifies tasks assigned to absent owners, projects whose owners are on leave, absent owners with no backup, overloaded owners (active projects >= 3 or active tasks >= 8), and reduced-bandwidth owners carrying overdue items.
  2. Routing returns the direct owner when availability is `active`.
  3. Routing returns the configured backup person when the owner is `leave` or `ooo` and a backup exists.
  4. Routing surfaces an escalation-needed signal when the owner is absent and no backup is configured.
  5. No routing action modifies Notion task or project ownership — changes are recommendations only.
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md — TDD RED phase: staffing_risk.py stub + failing test suite (all RISK/ROUT requirements)
- [ ] 14-02-PLAN.md — TDD GREEN phase: full detect_risks() and compute_routing_recommendation() implementation

### Phase 15: Daily Board Report Staffing Sections and Backward-Compat Guard
**Goal**: The daily board report surfaces staffing-aware risk sections and backup-aware action lines when a staffing snapshot is present, and falls back cleanly to board-only output when it is absent.
**Depends on**: Phase 14
**Requirements**: RPT-01, RPT-02, RPT-03, COMPAT-01
**Success Criteria** (what must be TRUE):
  1. Daily board report loads `staffing_snapshot.json` when present and fresh; it falls back to board-only mode with a warning when the snapshot is missing.
  2. Report includes staffing sections covering: people on leave or unusual availability, tasks with absent owners, projects with absent owners and no backup, and overloaded owners.
  3. Action lines mention the backup person (via registry Discord mention token) when the owner is absent and a backup is configured.
  4. Existing board-only daily report invocation continues to work without `people_state.json` present — staffing sections are skipped and no crash occurs.
**Plans**: 2 plans

Plans:
- [ ] 15-01-PLAN.md — TDD RED phase: failing tests for RPT-01, RPT-02, RPT-03, COMPAT-01
- [ ] 15-02-PLAN.md — GREEN phase: build_report() snapshot loading + format_daily_check_message() staffing sections

### Phase 16: Skill and Documentation Updates
**Goal**: The Hermes skill and supporting documentation accurately describe the three-layer state model, staffing-aware operator commands, routing rules, and daily report expectations so agents and operators have correct runtime guidance.
**Depends on**: Phase 15
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md` exists with the canonical JSON structure for availability, capacity, coordination, and source blocks, and explicitly states that assignments are derived from board cache.
  2. The `discord-notion-scrum-attribution` Hermes skill covers the three-layer state model, staffing-aware coordination goals, operator commands for leave/availability, routing rules for absent owners, and daily report expectations with staffing risk.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 11. People-State Schema, Store, and Contracts | 3/3 | Complete    | 2026-04-24 |
| 12. Operator CLI Write and Query Surface | 0/TBD | Not started | - |
| 13. Staffing Snapshot Derivation and Preflight Extensions | 3/3 | Complete    | 2026-04-24 |
| 14. Staffing Risk Module and Follow-Up Routing | 2/2 | Complete    | 2026-04-24 |
| 15. Daily Board Report Staffing Sections and Backward-Compat Guard | 0/TBD | Not started | - |
| 16. Skill and Documentation Updates | 0/TBD | Not started | - |

## Completed Phase History

<details>
<summary>✅ v2.0 Hermes Discord ↔ Notion Scrum Level 2+3 — SHIPPED 2026-04-22</summary>

- [x] Phase 8: Shared Workflow Modules (Level 2) — 5/5 plans complete
- [x] Phase 9: Operator Entrypoints, Contracts, and Adapter Boundary — 4/4 plans complete
- [x] Phase 10: Pattern Documentation and Test Coverage — 1/1 plan complete

Archived phase execution history:

- `.planning/milestones/v2.0-phases/08-shared-workflow-modules-level-2/`
- `.planning/milestones/v2.0-phases/09-operator-entrypoints-contracts-and-adapter-boundary/`
- `.planning/milestones/v2.0-phases/10-pattern-documentation-and-test-coverage/`

</details>

<details>
<summary>✅ v1.0 Python rewrite foundation — SHIPPED before v2.0 close</summary>

- [x] Phase 1: Project Bootstrap and CLI Skeleton
- [x] Phase 2: Config, Workspace, and Persistence Foundations
- [x] Phase 3: Ingest, Trim, and Tagging Migration
- [x] Phase 4: Variants, Hooks, and Pipeline Orchestration
- [x] Phase 5: External Integrations and Reporting
- [x] Phase 6: Hardening, Parity Verification, and Cutover Readiness

</details>

## Legacy Archive

- Legacy SharePoint live-auth backlog was intentionally moved out of active routing and archived at `.planning/archive/legacy/999.1-live-sharepoint-authentication-and-remote-transfer.md`.
