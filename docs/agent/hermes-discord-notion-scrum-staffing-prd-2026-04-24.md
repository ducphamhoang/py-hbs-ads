# PRD — Staffing-Aware Discord ↔ Notion Scrum Coordination

> Extend the current Discord↔Notion Scrum attribution workflow so Hermes can reason about assignment, real execution status, and team availability/leave — not just raw task rows — while keeping writes guarded and auditable.

---

## 1. Executive summary

The current workflow is already good at three things:
- resolving Discord senders safely,
- correlating replies to pending prompts,
- applying narrow Notion updates with guarded local scripts.

What it still lacks is **staffing awareness**.

Today the system can tell whether a task is overdue or ownerless. It cannot reliably answer higher-value operator questions like:
- who is currently carrying which project,
- whether a project is effectively blocked because its owner is on leave,
- whether a follow-up should be redirected to a backup instead of pinging the absent owner,
- whether one person is overloaded across too many active projects/tasks.

This PRD defines the next layer: a **people-state protocol** that sits beside the existing prompt and identity state. It should remain an outer-layer local workflow, not a Hermes core change.

---

## 2. Problem statement

### 2.1 Operational problem

The current Scrum automation is task-aware but not staffing-aware.

That creates four failure modes:
1. Hermes can ping the wrong person when the assigned owner is on leave.
2. Hermes can misread project health because Notion status alone hides execution reality.
3. Hermes cannot produce useful daily summaries about staffing bottlenecks.
4. Hermes cannot preserve short-lived but operationally important human state like `off this afternoon`, `leave until Friday`, or `reduced bandwidth this week`.

### 2.2 Product problem

The Scrum Master needs to reason over three linked layers:
- **board state** — projects/tasks in Notion,
- **people state** — availability, leave, backup, current load,
- **coordination state** — open prompts, clarifications, pending decisions.

The current implementation only handles the first and third layers well.

---

## 3. Product objective

Build a staffing-aware extension to the current Discord↔Notion Scrum workflow that:

1. tracks assignment at the person/project/task level,
2. stores structured availability and leave state outside Hermes core,
3. enriches daily/operator reports with staffing-aware risk signals,
4. changes follow-up behavior when the assigned person is absent or bandwidth-limited,
5. keeps read-only board inspection lightweight,
6. preserves the existing guarded-write philosophy,
7. is simple enough to operate from local JSON state plus thin scripts.

---

## 4. Non-goals

This phase does **not** aim to:
- replace Notion as the source of truth for projects/tasks,
- build a full HR/leave management system,
- infer leave or availability from unstructured chat without explicit confirmation,
- auto-reassign ownership silently,
- require Hermes core changes,
- create a heavy database-backed orchestration service.

---

## 5. Product thesis

The right design is to add a **first-class people-state layer** to the current workflow.

That layer should be:
- **structured** enough for safe automation,
- **local** enough for fast operator usage,
- **small** enough to inspect and repair manually,
- **derived where possible** from board cache and registry,
- **explicitly confirmed** for leave/availability facts that are not reliably present in Notion.

In practice:
- Notion remains the source of truth for project/task rows.
- `team_registry.json` remains the identity source of truth.
- a new local people-state file becomes the source of truth for short-horizon staffing reality.
- reports and prompts combine all three.

---

## 6. User stories

### 6.1 Operator / Scrum Master
- As an operator, I want to see which people are active on which projects right now.
- As an operator, I want Hermes to notice when a project owner is on leave.
- As an operator, I want a daily digest that highlights staffing risk, not just task hygiene.

### 6.2 Team member
- As a team member, I want to tell Hermes `t nghỉ phép tới 2026-04-28` and have later follow-ups respect that.
- As a team member, I want Hermes to ask for the exact missing thing instead of blindly pinging me while I am off.

### 6.3 Team lead
- As a team lead, I want to know who is overloaded, who is absent, and which active projects have no effective active owner.

---

## 7. Scope

### 7.1 In scope
- structured staffing state file(s)
- read-only staffing summary scripts
- leave/availability command surface
- workload/assignment derivation from board cache
- staffing-aware daily report output
- staffing-aware follow-up recommendation rules
- schema and tests for the new state
- skill and docs updates

### 7.2 Out of scope for this phase
- automatic reassignment in Notion
- syncing from external HR/calendar systems
- long-horizon capacity planning
- personal attendance analytics

---

## 8. Core concepts

### 8.1 Person state
Structured operational state about a canonical person, including:
- availability status,
- leave window,
- backup owner,
- bandwidth note,
- last-confirmed source.

### 8.2 Assignment state
A derived or cached view of:
- active projects led by a person,
- active tasks assigned to a person,
- counts by status,
- blocked/overdue items.

### 8.3 Staffing risk
A risk generated when people state changes the interpretation of board state, for example:
- task assigned to absent owner,
- project with owner on leave and no backup,
- overloaded owner with too many active projects/tasks,
- blocked task whose dependency owner is away.

---

## 9. Proposed file structure

### 9.1 Keep existing files
- `state/notion_scrum/team_registry.json`
- `state/notion_scrum/pending_prompts.json`
- `state/notion_scrum/audit_log.jsonl`
- `state/notion_scrum/cache/board_snapshot.json`

### 9.2 Add new state files
- `state/notion_scrum/people_state.json`
- `state/notion_scrum/cache/staffing_snapshot.json`

### 9.3 Add/update scripts
- Create: `scripts/notion_scrum/people_state_store.py`
- Create: `scripts/notion_scrum/update_people_state.py`
- Create: `scripts/notion_scrum/query_people_state.py`
- Create: `scripts/notion_scrum/build_staffing_snapshot.py`
- Create: `scripts/notion_scrum/staffing_risk_report.py`
- Modify: `scripts/notion_scrum/daily_board_report.py`
- Modify: `scripts/notion_scrum/preflight.py`
- Modify: `scripts/notion_scrum/result_contracts.py`
- Modify: `scripts/notion_scrum/process_inbound_reply.py` only in a later milestone if we support structured leave replies through the same prompt flow

### 9.4 Add/update docs
- Create: `docs/agent/hermes-discord-notion-scrum-staffing-prd-2026-04-24.md`
- Create: `docs/agent/hermes-discord-notion-scrum-staffing-state-schema.md`
- Create: `docs/plans/2026-04-24-notion-scrum-staffing-awareness.md`
- Modify: `docs/agent/hermes-discord-notion-scrum-skill-spec.md`
- Modify: `docs/agent/hermes-discord-notion-scrum-state-schema.md`
- Modify: `docs/agent/notion-scrum-template-catalog.md`
- Modify skill: `~/.hermes/skills/productivity/discord-notion-scrum-attribution/SKILL.md`

---

## 10. State model

### 10.1 `people_state.json`

Purpose:
- store explicit short-horizon staffing facts that do not naturally belong in Notion task rows.

Top-level shape:

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

#### Availability statuses
Allowed initial values:
- `active`
- `leave`
- `ooo`
- `partial`
- `unknown`

#### Bandwidth statuses
Allowed initial values:
- `normal`
- `reduced`
- `limited`
- `unknown`

### 10.2 `staffing_snapshot.json`

Purpose:
- store a read-optimized, derived view built from `board_snapshot.json` + `team_registry.json` + `people_state.json`.

Top-level shape:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-24T05:10:00Z",
  "inputs": {
    "board_snapshot_generated_at": "2026-04-24T05:08:00Z",
    "people_state_updated_at": "2026-04-24T05:00:00Z",
    "team_registry_updated_at": "2026-04-23T03:48:53Z"
  },
  "people": {
    "toanvt": {
      "canonical_person_key": "toanvt",
      "display_name": "toanvt",
      "availability_status": "leave",
      "leave_until": "2026-04-28",
      "bandwidth": "reduced",
      "backup_person_key": "ducph",
      "active_project_ids": ["project-1"],
      "active_project_titles": ["[CTB] Demo Project"],
      "active_task_ids": ["task-1", "task-2"],
      "active_task_titles": ["rough cut v1", "VO handoff"],
      "counts": {
        "active_projects": 1,
        "active_tasks": 2,
        "blocked_tasks": 1,
        "overdue_tasks": 0,
        "undated_tasks": 1
      },
      "risks": [
        "owner_on_leave",
        "has_active_tasks_while_on_leave"
      ]
    }
  },
  "project_effective_owners": {
    "project-1": {
      "title": "[CTB] Demo Project",
      "owner_person_keys": ["toanvt"],
      "effective_owner_person_keys": ["ducph"],
      "risk_flags": ["owner_absent_backup_used"]
    }
  }
}
```

### 10.3 Why split raw state vs snapshot

Keep two layers because they solve different problems:
- `people_state.json` = operator-maintained truth for availability/leave.
- `staffing_snapshot.json` = derived fast lookup for reports and routing.

This keeps writes simple and read paths fast.

---

## 11. Script responsibilities

### 11.1 `people_state_store.py`
Shared module for:
- loading/saving `people_state.json`
- schema validation
- transitions like set leave / clear leave / set bandwidth / set backup
- helper queries: `is_person_absent()`, `effective_followup_target()`

### 11.2 `update_people_state.py`
Primary operator command surface.

V1 should be a **structured CLI**, not a natural-language parser.

Recommended flags:
- `--person <canonical-or-resolvable-name>`
- `--action <set-leave|clear-leave|set-bandwidth|set-backup>`
- `--since <YYYY-MM-DD>`
- `--until <YYYY-MM-DD>`
- `--bandwidth <normal|reduced|limited|unknown>`
- `--backup <canonical-or-resolvable-name>`
- `--note <text>`
- `--execute`

Why: Hermes can produce structured commands safely, while a local CLI should not depend on brittle regex/NLP parsing of operator prose.

Default behavior:
- dry-run unless `--execute`
- resolve canonical person via registry first
- ambiguity stops write

### 11.3 `query_people_state.py`
Read-only lookup for:
- current status of one person
- who is on leave today
- who has reduced bandwidth
- backup routing lookup
- optionally `--json` / compact summary output

### 11.5 `build_staffing_snapshot.py`
Read-only derivation step that merges:
- `team_registry.json`
- `people_state.json`
- `cache/board_snapshot.json`

Outputs:
- `cache/staffing_snapshot.json`
- optional summary diagnostics

### 11.6 `staffing_risk_report.py`
Focused reporting helper for staffing-aware risk output.

Should compute at least:
- active tasks assigned to absent people
- active projects whose owners are absent
- active projects with no backup for absent owner
- overloaded owners by threshold
- reduced-bandwidth owners carrying urgent overdue items

### 11.7 `daily_board_report.py` changes
Current script already computes board hygiene and task urgency.
It should be extended to:
- load `people_state.json` and/or `staffing_snapshot.json`
- append staffing risk sections
- suppress or rewrite follow-up recommendations when owner is absent
- include backup mention when configured

### 11.8 `preflight.py` changes
Preflight should also validate:
- `people_state.json` exists or is safely bootstrappable
- referenced backup person keys exist in registry
- leave date windows are valid
- schema versions are supported
- snapshot freshness warnings are surfaced

---

## 12. Reporting requirements

### 12.1 Daily digest must add staffing-aware sections
New useful sections:
- `Người đang nghỉ / availability khác thường`
- `Task đang nằm ở người vắng mặt`
- `Project có owner nghỉ nhưng chưa có backup`
- `Người đang ôm quá nhiều việc active`

### 12.2 Recommended initial thresholds
Configurable but start with:
- overloaded if `active_projects >= 3` or `active_tasks >= 8`
- staffing risk if person is `leave`/`ooo` and still owns active project/task
- warning if `bandwidth in {reduced, limited}` and person has overdue items

### 12.3 Mention policy
Preserve existing registry-backed mention generation:
- prefer `<@discord_id> (DisplayName)`
- if absent owner has backup, mention backup in action line instead of absent owner
- keep tokenized mention mode for cron-safe delivery

---

## 13. Follow-up routing rules

### 13.1 Routing decision table

| Situation | Default behavior |
|---|---|
| Owner active | ask owner normally |
| Owner on leave + backup exists | ask backup, note owner leave window |
| Owner on leave + no backup | escalate to operator/lead, do not blind-ping owner |
| Owner partial/reduced bandwidth | ask owner only if low urgency; otherwise include backup/lead |
| Owner unknown in registry | block attribution-sensitive write |

### 13.2 Important safety rule
Staffing state can change **who to ask**, but should not by itself change Notion ownership.

That means:
- reroute follow-up safely,
- do not auto-reassign board owner unless explicitly commanded.

---

## 14. Skill changes

The `discord-notion-scrum-attribution` skill should gain a new section covering:
- staffing-aware coordination goals,
- distinction between identity registry vs people-state vs board cache,
- operator commands for leave/availability updates,
- routing rules for absent owners,
- daily report expectations with staffing risk,
- ambiguity rules for person-state writes.

The skill should still keep wrapper-first guidance.

---

## 15. Backward compatibility

The rollout should be additive.

Existing behavior should keep working if `people_state.json` is missing by:
- treating availability as `unknown`,
- skipping staffing-specific sections,
- surfacing a warning rather than failing read-only workflows.

Live writes that explicitly target people-state should fail safely if the state file is invalid.

---

## 16. Risks

### 16.1 State drift
Local people-state may become stale.

Mitigation:
- store `updated_at`, `source`, `confirmed_by`
- show stale-state warnings in queries/reports
- optionally add `expires_at` later for temporary statuses

### 16.2 Over-automation
The system might start acting as if leave state implies reassignment.

Mitigation:
- explicit rule: routing changes are allowed; ownership changes are not implicit

### 16.3 Ambiguous person references
Human commands like `Ma nghỉ phép` can fail if `Ma` is not uniquely mapped.

Mitigation:
- resolve via registry aliases + Discord identity
- ambiguity stops write

### 16.4 Too much fragmentation
Adding too many small files can recreate the same sprawl problem.

Mitigation:
- centralize all people-state logic in `people_state_store.py`
- keep operator surfaces thin

---

## 17. Acceptance criteria

This phase is successful when all are true:

1. Operator can set/clear leave and bandwidth state with guarded commands.
2. System can answer who is on leave, who has reduced bandwidth, and who backs them up.
3. Daily report surfaces staffing-aware risk in addition to current task/project hygiene.
4. Follow-up logic can recommend or compute the effective target when owner is absent.
5. Preflight validates people-state integrity.
6. Tests cover schema validation, state transitions, snapshot derivation, and staffing-risk detection.
7. Existing board-only workflows remain backward compatible.

---

## 18. Open design decisions

Most of the main architecture is now fixed. The remaining open decisions are intentionally narrow:

1. Whether leave windows should support date-only first, datetime later.
2. Whether staffing snapshot generation should be a standalone step or embedded in `daily_board_report.py` when cache is fresh.
3. Whether `staffing_risk_report.py` should be a reusable module only or a standalone operator CLI as well.

Already decided before implementation starts:
- date-only leave windows first,
- assignments derived from board cache,
- standalone staffing snapshot builder,
- operator-command write path first.

Important milestone boundary:
- **Prompt-driven leave intake via Discord replies is out of scope for this phase and should be treated as a separate milestone.** It would require prompt schema changes, template additions, inbound-reply planning changes, and new audit/result handling. It is not a small follow-on tweak.

---

## 19. Recommended rollout order

1. Add schema + store module + explicit result-contract additions for staffing (`effective_followup_person_key`, `routing_reason`).
2. Add read-only query/update wrappers for people-state.
3. Add staffing snapshot derivation.
4. Add staffing risk module/CLI and then extend daily report with staffing sections.
5. Patch skill/docs.
6. Treat prompt-driven leave follow-up as a separate milestone later.

---

## 20. Summary recommendation

This is a reasonable next step.

The important architectural choice is **not** to shove staffing facts into the existing registry or pending-prompt files. Keep them in a dedicated people-state layer, then derive a separate staffing snapshot for reporting and routing.

That gives the workflow a clean three-layer model:
- identity (`team_registry.json`)
- coordination (`pending_prompts.json`)
- staffing (`people_state.json`)

That split is simple, operationally legible, and consistent with the way the current system already works.
