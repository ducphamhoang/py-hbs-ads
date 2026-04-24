# Hermes Discord↔Notion Scrum Staffing State Schema

## 1. Overview

`people_state.json` stores explicit short-horizon staffing facts for the Hermes Discord↔Notion Scrum staffing-awareness workflow. It is the operator-maintained source of truth for availability, leave, backup routing, and bandwidth facts that do not naturally belong in Notion task rows.

It is intentionally separate from the other state files:

- `team_registry.json` is the static identity and contact registry. It resolves canonical person keys, aliases, and mention-safe contact identity.
- `pending_prompts.json` is the coordination queue of outbound messages that were sent and are still awaiting reply or resolution.
- `people_state.json` is the staffing layer. It stores confirmed operational person state that changes how follow-up routing and staffing-aware reporting should behave.

This split keeps identity, coordination, and staffing concerns separate and auditable.

## 2. Top-level structure

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

## 3. Per-person record structure

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

## 4. Bootstrap empty container

Minimal valid JSON:

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-04-24T05:00:00Z",
  "people": {}
}
```

This is the safe bootstrapped container when no staffing records have been written yet.

## 5. Full populated example

PRD section 10.1 provides this populated example for `toanvt` on leave with `ducph` as backup:

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

## 6. Validation rules

- `availability.status` must be one of `active`, `leave`, `ooo`, `partial`, or `unknown`.
- `capacity.bandwidth` must be one of `normal`, `reduced`, `limited`, or `unknown`.
- Date window constraint: `until >= since` when both are present, and both values must use `YYYY-MM-DD`.
- `backup_person_key` must reference a canonical person key that exists in `team_registry.json`.
- All `updated_at` fields must be valid ISO8601 datetime strings.
- The top-level `updated_at` must also be valid ISO8601.
- `last_status_check_at` must be either a valid ISO8601 datetime string or `null`.
- `people` must be an object keyed by canonical person key strings.
- `schema_version` must be the supported literal value `"1.0"`.

## 7. Assignments Are Derived From Board Cache

Assignments are not manually entered in `people_state.json`.

They are derived from the board cache instead, because project and task ownership already belong to the Notion board state and should remain sourced from that operational truth. The PRD explicitly fixes this boundary: assignments are derived from board cache, while `people_state.json` stores only staffing facts such as leave, bandwidth, backup, and routing metadata.

Assignment and load data therefore live in derived read models built from:

- `state/notion_scrum/cache/board_snapshot.json`
- `state/notion_scrum/team_registry.json`
- `state/notion_scrum/people_state.json`

The main derived output is `state/notion_scrum/cache/staffing_snapshot.json`, which holds assignment-oriented data such as active projects, active tasks, counts, effective owners, and staffing risk flags.

## 8. Routing decision table

| availability.status | backup_person_key present | routing outcome |
|---|---|---|
| `active` | yes or no | assign to owner |
| `leave` | yes | assign to backup |
| `leave` | no | escalate |
| `unknown` | yes or no | block and prompt |

## 9. Derived Staffing Snapshot

`cache/staffing_snapshot.json` is a read-optimized derived artifact built from three inputs:

- `people_state.json` (availability, bandwidth, backup, routing facts)
- `state/notion_scrum/cache/board_snapshot.json` (project and task ownership from Notion)
- `state/notion_scrum/team_registry.json` (canonical identity and alias resolution)

Generated by: `build_staffing_snapshot.py`

This file is **not operator-maintained**. It is always re-derived and must never be edited manually. If it is stale or absent, re-run `build_staffing_snapshot.py` before running staffing-aware workflows.

The snapshot is treated as fresh if it was generated within the current operational window; otherwise it is treated as stale or absent and the daily board report falls back to board-only mode.

**Assignments in the snapshot are derived from `board_snapshot.json` + `team_registry.json`. They are never manually entered in `people_state.json`.**

### 9.1 Top-level snapshot structure

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

## 10. Operator Commands

> **Safety rule: All writes require `--execute`. The default for every write command is dry-run. Always review dry-run output before executing with `--execute`.**

### 10.1 Write path — `update_people_state.py`

```
# Mark person on leave
update_people_state.py --person <alias> --action set_leave --until YYYY-MM-DD [--backup <alias>] [--note "..."] [--execute]

# Clear leave status
update_people_state.py --person <alias> --action clear_leave [--execute]

# Update bandwidth
update_people_state.py --person <alias> --action set_bandwidth --bandwidth reduced|limited|normal [--execute]

# Set standing backup routing
update_people_state.py --person <alias> --action set_backup --backup <alias> [--execute]
```

### 10.2 Read path — `query_people_state.py` (no preflight required)

```
# Check one person's current state
query_people_state.py --person <alias>

# List everyone on leave today
query_people_state.py --on-leave-today

# List people on reduced bandwidth
query_people_state.py --reduced-bandwidth

# Find who is backup for a given person
query_people_state.py --backup-for <alias>
```

### 10.3 Backup field disambiguation

Two distinct backup fields exist in each person record:

- `availability.backup_person_key` — leave-specific backup. Applies only while the leave window is active. Set via `--action set_leave --backup <alias>`.
- `coordination.backup_person_key` — standing policy-level routing target. Used regardless of whether the person is currently on leave. Set via `--action set_backup --backup <alias>`.

Both fields accept canonical person keys validated against `team_registry.json`.
