# Staffing & People State Management

**Canonical source for staffing awareness, leave management, backup routing, and risk detection.**

This document combines:
- `people_state.json` schema and operator commands
- Staffing snapshot derivation and risk categories
- Daily report integration for staffing-aware workflows

> **Key principle:** Assignments derive from board cache, not people state. People state stores only staffing facts (leave, bandwidth, backup routing) that change how follow-up decisions should behave.

---

## Quick Reference (Micro-Glossary)

| Term | Meaning |
|---|---|
| **Availability status** | Current state of a person: `active`, `leave`, `ooo` (out-of-office), `partial`, `unknown` |
| **Bandwidth** | Capacity level: `normal`, `reduced`, `limited`, `unknown` |
| **Backup person key** | Canonical identity of the fallback for routing when owner is unavailable |
| **Staffing snapshot** | Derived JSON artifact (read-only) that combines board ownership + people state + risks |
| **Assignment boundary** | CRITICAL: Task/project owners always derive from `board_snapshot.json`, never from `people_state.json` |
| **Risk flag** | Automated detection of staffing issues (absent owner, no backup, overload, bandwidth conflict) |
| **Routing recommendation** | Suggested target person for a task based on owner availability and backup policy |

---

## 1. Overview

`people_state.json` stores explicit short-horizon staffing facts for the Hermes Discord↔Notion Scrum staffing-awareness workflow. It is the operator-maintained source of truth for availability, leave, backup routing, and bandwidth facts that do not naturally belong in Notion task rows.

It is intentionally separate from other state files:

- `team_registry.json` is the static identity and contact registry. It resolves canonical person keys, aliases, and mention-safe contact identity.
- `pending_prompts.json` is the coordination queue of outbound messages still awaiting reply.
- `board_snapshot.json` (in cache/) is the authoritative project/task ownership snapshot.
- `people_state.json` is the staffing layer. It stores confirmed operational person state that changes how follow-up routing should behave.

This split keeps identity, coordination, board assignments, and staffing concerns separate and auditable.

---

## 2. Top-level Structure

`people_state.json` has this top-level shape:

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-24T05:00:00Z",
  "people": {}
}
```

Top-level fields:

- `schema_version`: string literal, must be exactly `"1.0"`.
- `updated_at`: ISO8601 datetime string indicating when the file was last updated.
- `people`: object keyed by `canonical_person_key` string.

Each key under `people` is the canonical person key for that record, for example `toanvt` or `ducph`.

---

## 3. Per-person Record Structure

Each entry inside `people` is a per-person record keyed by canonical person key.

```json
{
  "canonical_person_key": "toanvt",
  "availability": {
    "status": "leave",
    "since": "2026-04-24",
    "until": "2026-04-28",
    "timezone": "Asia/Ho_Chi_Minh",
    "half_day": null,
    "note": "nghi phep",
    "backup_person_key": "ducph",
    "source": {
      "kind": "manual_command",
      "platform": "discord",
      "platform_user_id": "400303290174144512",
      "message_id": null,
      "confirmed_by": "ducph"
    },
    "updated_at": "2026-04-24T05:00:00Z"
  },
  "capacity": {
    "bandwidth": "reduced",
    "note": "chi online buoi sang",
    "updated_at": "2026-04-24T05:00:00Z"
  },
  "coordination": {
    "default_followup_policy": "route_to_backup",
    "backup_person_key": "ducph",
    "last_status_check_at": "2026-04-24T05:00:00Z"
  },
  "metadata": {
    "tags": ["leave", "confirmed"],
    "last_actor_person_key": "ducph"
  }
}
```

Field definitions:

- `canonical_person_key`: string. Canonical identity key for the person record.

`availability` object:

- `status`: enum string. Allowed values: `active`, `leave`, `ooo`, `partial`, `unknown`.
- `since`: date string in `YYYY-MM-DD`.
- `until`: date string in `YYYY-MM-DD`.
- `timezone`: IANA timezone string such as `Asia/Ho_Chi_Minh`.
- `half_day`: nullable boolean. Use `true` or `false` when half-day semantics are explicitly known; otherwise `null`.
- `note`: free-text string describing the availability state.
- `backup_person_key`: nullable string. Canonical person key of the designated backup for this availability state.
- `source`: object describing where the staffing fact came from.
- `updated_at`: ISO8601 datetime string for the last update to the availability sub-object.

`availability.source` object:

- `kind`: string describing the source type, for example `manual_command`.
- `platform`: string naming the source platform, for example `discord`.
- `platform_user_id`: string with the platform-specific user identifier.
- `message_id`: nullable string. Source message identifier when applicable; otherwise `null`.
- `confirmed_by`: string naming the canonical person key that confirmed the fact.

`capacity` object:

- `bandwidth`: enum string. Allowed values: `normal`, `reduced`, `limited`, `unknown`.
- `note`: free-text string describing the bandwidth condition.
- `updated_at`: ISO8601 datetime string for the last update to the capacity sub-object.

`coordination` object:

- `default_followup_policy`: string describing the routing policy, for example `route_to_backup`.
- `backup_person_key`: nullable string. Coordination-level backup target for follow-up routing.
- `last_status_check_at`: ISO8601 datetime string or `null`.

`metadata` object:

- `tags`: array of strings for lightweight operator labels.
- `last_actor_person_key`: string naming the canonical person key of the last actor who changed the record.

---

## 4. Bootstrap and Examples

Minimal valid JSON:

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-24T05:00:00Z",
  "people": {}
}
```

This is the safe bootstrapped container when no staffing records have been written yet.

Full populated example for `toanvt` on leave with `ducph` as backup:

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-24T05:00:00Z",
  "people": {
    "toanvt": {
      "canonical_person_key": "toanvt",
      "availability": {
        "status": "leave",
        "since": "2026-04-24",
        "until": "2026-04-28",
        "timezone": "Asia/Ho_Chi_Minh",
        "half_day": null,
        "note": "nghỉ phép",
        "backup_person_key": "ducph",
        "source": {
          "kind": "manual_command",
          "platform": "discord",
          "platform_user_id": "400303290174144512",
          "message_id": null,
          "confirmed_by": "ducph"
        },
        "updated_at": "2026-04-24T05:00:00Z"
      },
      "capacity": {
        "bandwidth": "reduced",
        "note": "chỉ online buổi sáng",
        "updated_at": "2026-04-24T05:00:00Z"
      },
      "coordination": {
        "default_followup_policy": "route_to_backup",
        "backup_person_key": "ducph",
        "last_status_check_at": "2026-04-24T05:00:00Z"
      },
      "metadata": {
        "tags": ["leave", "confirmed"],
        "last_actor_person_key": "ducph"
      }
    }
  }
}
```

---

## 5. Validation Rules

- `availability.status` must be one of `active`, `leave`, `ooo`, `partial`, or `unknown`.
- `capacity.bandwidth` must be one of `normal`, `reduced`, `limited`, or `unknown`.
- Date window constraint: `until >= since` when both are present, and both values must use `YYYY-MM-DD`.
- `backup_person_key` must reference a canonical person key that exists in `team_registry.json`.
- All `updated_at` fields must be valid ISO8601 datetime strings.
- The top-level `updated_at` must also be valid ISO8601.
- `last_status_check_at` must be either a valid ISO8601 datetime string or `null`.
- `people` must be an object keyed by canonical person key strings.
- `schema_version` must be the supported literal value `"1.0"`.

---

## 6. Assignment Boundary (CRITICAL)

**Rule:** Active project/task assignments ALWAYS derive from:
- `board_snapshot.json` owner_ids (authoritative source of truth)
- `team_registry.json` Notion user ID mappings

**Never from:** `people_state.json`

**Why?** Decoupling: people_state is transient state (leave, bandwidth). Board is source of truth. Board snapshot must be fresh when computing staffing snapshot.

**Consequence:** Setting `people_state.json::coordination.backup_person_key` does NOT auto-update Notion page ownership. It is a routing hint, not a board mutation.

When an absent person returns: Their existing assignments remain in the board. Routing automatically falls back to normal (routes to the owner again).

---

## 7. Staffing Snapshot Operations

### 7.1 When is Staffing Awareness Active?

- Staffing awareness activates when `state/notion_scrum/cache/staffing_snapshot.json` exists
- Without snapshot → agents fall back to board_cache-only mode (COMPAT-01)
- Snapshot is optional; all core operations work without it

### 7.2 Building Staffing Snapshot

**Tool:** `build_staffing_snapshot.py`
**Inputs:** team_registry.json, people_state.json, board_snapshot.json
**Output:** staffing_snapshot.json

Pattern:
```python
from build_staffing_snapshot import build_staffing_snapshot
registry = load_registry(DEFAULT_TEAM_REGISTRY)
people_state = load_people_state(DEFAULT_PEOPLE_STATE)
board_snapshot = load_json(DEFAULT_BOARD_CACHE)
snapshot = build_staffing_snapshot(registry, people_state, board_snapshot, today_iso)
save_json(DEFAULT_STAFFING_SNAPSHOT, snapshot)
```

Snapshot includes:
- Per-person active projects/tasks/overdue counts
- Risk flags (absent_owner, absent_no_backup)
- Backup person keys
- Project effective owners
- Unresolved owner IDs

**Cache freshness:** Snapshot should be refreshed whenever board_snapshot is updated.

### 7.3 Derived Staffing Snapshot Structure

`cache/staffing_snapshot.json` is a read-optimized derived artifact built from three inputs:

- `people_state.json` (availability, bandwidth, backup, routing facts)
- `state/notion_scrum/cache/board_snapshot.json` (project and task ownership from Notion)
- `state/notion_scrum/team_registry.json` (canonical identity and alias resolution)

Generated by: `build_staffing_snapshot.py`

This file is **not operator-maintained**. It is always re-derived and must never be edited manually. If it is stale or absent, re-run `build_staffing_snapshot.py` before running staffing-aware workflows.

**Top-level snapshot structure:**

```json
{
  "generated_at": "2026-04-25T08:00:00Z",
  "people": {
    "<person_key>": {
      "display_name": "...",
      "availability_status": "active|leave|ooo|unknown",
      "leave_window": { "from": "YYYY-MM-DD", "until": "YYYY-MM-DD" },
      "backup_person_key": "<key or null>",
      "active_projects": [...],
      "active_tasks": [...],
      "risk_flags": [...]
    }
  },
  "project_effective_owners": {
    "<project_id>": "<effective_person_key>"
  }
}
```

Field notes:

- `people`: per-person summary keyed by canonical person key. Includes display name, derived availability status, leave window (when applicable), backup key, lists of active project and task IDs and titles, and any detected risk flags.
- `project_effective_owners`: map from project ID to the effective owner key after applying leave/backup substitution. Used by the daily board report to produce correct action lines.

---

## 8. Operator Commands

> **Safety rule: All writes require `--execute`. The default for every write command is dry-run. Always review dry-run output before executing with `--execute`.**

### 8.1 Write path — `update_people_state.py`

```bash
# Mark person on leave
update_people_state.py --person <alias> --action set_leave --until YYYY-MM-DD [--backup <alias>] [--note "..."] [--execute]

# Clear leave status
update_people_state.py --person <alias> --action clear_leave [--execute]

# Update bandwidth
update_people_state.py --person <alias> --action set_bandwidth --bandwidth reduced|limited|normal [--execute]

# Set standing backup routing
update_people_state.py --person <alias> --action set_backup --backup <alias> [--execute]
```

### 8.2 Read path — `query_people_state.py` (no preflight required)

```bash
# Check one person's current state
query_people_state.py --person <alias>

# List everyone on leave today
query_people_state.py --on-leave-today

# List people on reduced bandwidth
query_people_state.py --reduced-bandwidth

# Find who is backup for a given person
query_people_state.py --backup-for <alias>
```

### 8.3 Backup field disambiguation

Two distinct backup fields exist in each person record:

- `availability.backup_person_key` — leave-specific backup. Applies only while the leave window is active. Set via `--action set_leave --backup <alias>`.
- `coordination.backup_person_key` — standing policy-level routing target. Used regardless of whether the person is currently on leave. Set via `--action set_backup --backup <alias>`.

Both fields accept canonical person keys validated against `team_registry.json`.

---

## 9. Staffing Risk Detection

### 9.1 When Risks Are Detected

**Tool:** `staffing_risk.py::detect_risks(snapshot)`
**Output:** Five risk categories (see § 9.2)

When to call:
- Daily board report generation
- Before routing decisions for absent-owner tasks
- Operator queries for staffing status

Thresholds (configurable):
- overload_projects_threshold: 3 (default)
- overload_tasks_threshold: 8 (default)

### 9.2 Five Risk Categories

Returned by `detect_risks(staffing_snapshot)`:

#### RISK-01: absent_owner_tasks

Tasks assigned to people who are currently absent (leave/ooo).
Includes backup person key if assigned.

Use: Alert follow-up agents to route task to backup. Update daily report.

#### RISK-02: absent_owner_projects

Projects with effective owner who is absent.

Use: Escalate project status checks. Notify stakeholders.

#### RISK-03: absent_no_backup

People marked absent with NO backup assigned.

**Critical risk.** People who are gone + unreachable = potential blocker.

Use: Route all their tasks to manager. Send notification.

#### RISK-04: overloaded_owners

People with 3+ projects OR 8+ tasks (thresholds configurable).

Use: Offer capacity reduction. Alert manager.

#### RISK-05: reduced_bandwidth_with_overdue

People with reduced/limited bandwidth AND >0 overdue tasks.

Use: Increase support. Extend deadlines.

### 9.3 Threshold Configuration

In `staffing_risk.py`:
```python
detect_risks(
    snapshot,
    overload_projects_threshold=3,
    overload_tasks_threshold=8
)
```

Default thresholds: 3 projects, 8 tasks.
Override via function arguments or config file (to be specified).

---

## 10. Daily Report Integration

`daily_board_report.py` conditionally loads `cache/staffing_snapshot.json` to generate staffing-aware sections alongside the standard board output.

### 10.1 When the Snapshot is Present and Fresh

The report includes the following staffing sections:

- **People on leave or unusual availability** — Lists everyone whose status is `leave`, `ooo`, `partial`, or `unknown`.
- **Tasks with absent owners** — Lists tasks from risk category 1 (absent-owner tasks).
- **Projects with absent owners and no backup** — Lists projects from risk categories 2 and 3.
- **Overloaded owners** — Lists people from risk category 4.

Action lines in these sections mention the backup person using the registry Discord mention token (e.g. `<@discord_user_id>`) when a backup is configured.

### 10.2 When the Snapshot is Absent or Stale

The report falls back to board-only mode with a warning logged to output. Staffing sections are silently skipped. No crash or error occurs.

This is a valid operational state — not an error. Operators running board-only workflows (before running `build_staffing_snapshot.py`) are not blocked. The board-only invocation path is preserved as a first-class operational mode.

---

## 11. Computing Routing Recommendations

**Tool:** `staffing_risk.py::compute_routing_recommendation(snapshot_person, people_state=None)`
**Output:** (target_person_key, routing_reason)

Routing decisions:
- If owner active → route to owner
- If owner absent + backup → route to backup (reason: owner_absent_backup_used)
- If owner absent + no backup → route to manager/admin (reason: owner_absent_no_backup)

**Critical:** Recommendations are observation-only. Never mutate Notion page ownership.

---

## 12. Routing Decision Table

| availability.status | backup_person_key present | routing outcome |
|---|---|---|
| `active` | yes or no | assign to owner |
| `leave` | yes | assign to backup |
| `leave` | no | escalate |
| `unknown` | yes or no | block and prompt |

---

**Last updated:** 2026-04-29  
**Canonical source for:** Staffing facts, people state, risk detection, routing guidance  
**Contact:** See `.planning/PROJECT.md`
