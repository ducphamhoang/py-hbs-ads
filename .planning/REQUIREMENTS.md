# Requirements: py-hbs-ads

**Defined:** 2026-04-24
**Core Value:** Provide one maintainable Python CLI and automation contract for ad-production operations without regressing operational clarity, safety, attribution, or migration practicality.

---

## Milestone v3.0 Requirements — Staffing-Aware Discord↔Notion Scrum

**Milestone goal:** Add a people-state layer so Hermes can track leave/availability, derive assignment risk, and produce staffing-aware follow-ups and reports without weakening guarded-write safety.

### STATE — People-state schema and store module

- [x] **STATE-01**: System can load and save a valid `people_state.json` with schema-version, updated_at, and people map.
- [x] **STATE-02**: System validates `availability.status` against allowed enum (`active`, `leave`, `ooo`, `partial`, `unknown`) and rejects invalid values.
- [x] **STATE-03**: System validates `capacity.bandwidth` against allowed enum (`normal`, `reduced`, `limited`, `unknown`) and rejects invalid values.
- [x] **STATE-04**: System rejects leave date windows where `until < since`.
- [x] **STATE-05**: System rejects backup person keys not present in `team_registry.json` when registry is provided.
- [x] **STATE-06**: Operator can apply `set_leave` transition (status, since, until, backup, note) via store module.
- [x] **STATE-07**: Operator can apply `clear_leave` transition to reset availability to `active` or `unknown` via store module.
- [x] **STATE-08**: Operator can apply `set_bandwidth` and `set_backup` transitions via store module.
- [x] **STATE-09**: System can query whether a person is absent (`is_person_absent`) and compute effective follow-up target (`effective_followup_target`) via store module.
- [x] **STATE-10**: Result envelopes include `effective_followup_person_key` and `routing_reason` fields per stable contract.

### SCLI — Operator CLI surfaces for staffing state

- [ ] **SCLI-01**: Operator can update staffing state via `update_people_state.py` with structured flags (`--person`, `--action`, `--until`, `--bandwidth`, `--backup`, `--note`) and dry-run default.
- [ ] **SCLI-02**: `update_people_state.py` writes only when `--execute` is provided; dry-run output describes intended change.
- [ ] **SCLI-03**: `update_people_state.py` stops and surfaces an ambiguity error when a person alias maps to multiple registry candidates.
- [ ] **SCLI-04**: Operator can query staffing state via `query_people_state.py` with modes: `--person`, `--on-leave-today`, `--reduced-bandwidth`, `--backup-for`.
- [ ] **SCLI-05**: `query_people_state.py` is read-only and requires no preflight for basic queries.

### SNAP — Derived staffing snapshot

- [x] **SNAP-01**: System generates `cache/staffing_snapshot.json` from `team_registry.json` + `people_state.json` + `cache/board_snapshot.json` via `build_staffing_snapshot.py`.
- [x] **SNAP-02**: Snapshot includes per-person: display name, availability status, leave window, backup key, active project IDs/titles, active task IDs/titles, counts (active projects, tasks, blocked, overdue, undated), and risk flags.
- [x] **SNAP-03**: Snapshot derives assignments from board cache owner IDs and registry notion mappings — not from manually entered data in `people_state.json`.
- [x] **SNAP-04**: Snapshot includes `project_effective_owners` map with effective owner keys considering leave/backup.

### RISK — Staffing risk detection and reporting

- [x] **RISK-01**: System identifies tasks assigned to absent owners.
- [x] **RISK-02**: System identifies projects whose owners are on leave.
- [x] **RISK-03**: System identifies absent owners with no backup configured.
- [x] **RISK-04**: System identifies overloaded owners (default threshold: `active_projects >= 3` OR `active_tasks >= 8`).
- [x] **RISK-05**: System identifies reduced-bandwidth owners carrying overdue items.

### RPT — Daily board report with staffing-aware sections

- [x] **RPT-01**: Daily board report loads `staffing_snapshot.json` when present and fresh; falls back to board-only mode with a warning when missing.
- [x] **RPT-02**: Report includes staffing sections: people on leave/unusual availability, tasks with absent owners, projects with absent owners and no backup, overloaded owners.
- [x] **RPT-03**: Report action lines mention backup person (via registry Discord mention token) when owner is absent and backup exists.

### PRE — Preflight people-state integrity checks

- [x] **PRE-01**: Preflight warns (not errors) when `people_state.json` is missing for read-only workflows.
- [x] **PRE-02**: Preflight errors when `people_state.json` is present but invalid (bad schema, unsupported version) for staffing-aware write operations.
- [x] **PRE-03**: Preflight validates that all backup person keys in `people_state.json` exist in `team_registry.json`.
- [x] **PRE-04**: Preflight validates that leave date windows are logically valid (`since <= until`, dates parseable).

### ROUT — Staffing-aware follow-up routing

- [x] **ROUT-01**: System routes follow-up to the direct owner when owner availability is `active`.
- [x] **ROUT-02**: System routes follow-up to backup person when owner is `leave`/`ooo` and backup is configured.
- [x] **ROUT-03**: System surfaces escalation-needed signal when owner is absent and no backup is configured.
- [x] **ROUT-04**: Routing logic never modifies Notion task ownership — changes are recommendation/prompt only.

### COMPAT — Backward compatibility

- [x] **COMPAT-01**: Existing board-only daily report continues to work when `people_state.json` is absent — staffing sections are skipped, no crash.
- [x] **COMPAT-02**: Missing `people_state.json` is treated as `unknown` availability throughout all read paths.

### DOCS — Skill and documentation updates

- [ ] **DOCS-01**: `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md` created with canonical JSON structure for availability, capacity, coordination, and source blocks.
- [ ] **DOCS-02**: Hermes `discord-notion-scrum-attribution` skill updated with three-layer state model, staffing-aware coordination goals, operator commands, routing rules, and daily report expectations.

---

## Future Requirements (v4.0+)

### Prompt-driven leave intake

- **LEAVE-01**: Team member can tell Hermes `nghỉ phép tới YYYY-MM-DD` via Discord and have leave state recorded automatically — requires prompt schema changes, template additions, and inbound-reply planning changes. Out of scope for v3.0.

### Automatic reassignment

- **ASSIGN-01**: System auto-reassigns Notion task ownership when owner is on leave — deliberately deferred; routing changes are allowed in v3.0 but ownership mutation is not.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Prompt-driven leave intake via Discord replies | Requires prompt schema changes and inbound-reply pipeline extensions — separate milestone |
| Auto-reassignment of Notion task/project ownership | Explicitly prohibited in v3.0; routing changes follow-up target, not board ownership |
| Syncing from external HR or calendar systems | Out of scope per PRD §4 |
| Long-horizon capacity planning or attendance analytics | Out of scope per PRD §4 |
| GUI or dashboard delivery | Not in active scope per PROJECT.md |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STATE-01 | Phase 11 | Complete |
| STATE-02 | Phase 11 | Complete |
| STATE-03 | Phase 11 | Complete |
| STATE-04 | Phase 11 | Complete |
| STATE-05 | Phase 11 | Complete |
| STATE-06 | Phase 11 | Complete |
| STATE-07 | Phase 11 | Complete |
| STATE-08 | Phase 11 | Complete |
| STATE-09 | Phase 11 | Complete |
| STATE-10 | Phase 11 | Complete |
| COMPAT-02 | Phase 11 | Complete |
| SCLI-01 | Phase 12 | Pending |
| SCLI-02 | Phase 12 | Pending |
| SCLI-03 | Phase 12 | Pending |
| SCLI-04 | Phase 12 | Pending |
| SCLI-05 | Phase 12 | Pending |
| SNAP-01 | Phase 13 | Complete |
| SNAP-02 | Phase 13 | Complete |
| SNAP-03 | Phase 13 | Complete |
| SNAP-04 | Phase 13 | Complete |
| PRE-01 | Phase 13 | Complete |
| PRE-02 | Phase 13 | Complete |
| PRE-03 | Phase 13 | Complete |
| PRE-04 | Phase 13 | Complete |
| RISK-01 | Phase 14 | Complete |
| RISK-02 | Phase 14 | Complete |
| RISK-03 | Phase 14 | Complete |
| RISK-04 | Phase 14 | Complete |
| RISK-05 | Phase 14 | Complete |
| ROUT-01 | Phase 14 | Complete |
| ROUT-02 | Phase 14 | Complete |
| ROUT-03 | Phase 14 | Complete |
| ROUT-04 | Phase 14 | Complete |
| RPT-01 | Phase 15 | Complete |
| RPT-02 | Phase 15 | Complete |
| RPT-03 | Phase 15 | Complete |
| COMPAT-01 | Phase 15 | Complete |
| DOCS-01 | Phase 16 | Pending |
| DOCS-02 | Phase 16 | Pending |

**Coverage:**
- v3.0 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after v3.0 roadmap created*
