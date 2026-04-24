# Skill Spec — Hermes Discord ↔ Notion Scrum Attribution

This document specifies the **skill-layer behavior** for running Hermes as a Scrum Master in a public Discord thread while using external local scripts/state for attribution and Notion updates.

This is a **behavior spec**, not a Hermes core design.

---

## 1. Purpose

The skill should let Hermes:
- operate in a shared/public Discord thread
- ask targeted follow-up questions about Notion projects/tasks
- identify which human replied using Discord runtime metadata plus a local registry
- correlate a reply with a pending Scrum question
- apply safe Notion updates only when confidence is high
- ask for clarification instead of writing when confidence is low

The skill must assume:
- Hermes core is unchanged
- state is stored externally in local JSON files
- deterministic matching lives in helper scripts

---

## 2. Trigger conditions

Load this skill when all of these are true:
- session source is Discord
- conversation occurs in a public/shared thread or a coordination channel bound to this workflow
- the user asks Hermes to act as Scrum Master / traffic manager / task follow-up coordinator
- the workflow targets a Notion project/task board

This skill is especially appropriate when:
- multiple humans may respond in the same thread
- task ownership and follow-up attribution matter
- Hermes is expected to write updates back to Notion

---

## 3. Core operating stance

The skill should treat the thread as:
- a **shared conversation context** for human readability
- but **not** as the source of truth for attribution logic

The source of truth for reliable automation is:
1. Discord runtime sender metadata
2. local team registry
3. local pending prompt ledger
4. deterministic script outputs
5. Notion board state

The model may reason over the thread, but **writes must be gated by structured state**.

---

## 4. Required local artifacts

The skill should assume these artifacts exist or can be created:

### State files
- `~/work/py-hbs-ads/state/notion_scrum/team_registry.json`
- `~/work/py-hbs-ads/state/notion_scrum/pending_prompts.json`
- `~/work/py-hbs-ads/state/notion_scrum/audit_log.jsonl`

### Scripts
- `~/work/py-hbs-ads/scripts/notion_scrum/resolve_person.py`
- `~/work/py-hbs-ads/scripts/notion_scrum/record_pending_prompt.py`
- `~/work/py-hbs-ads/scripts/notion_scrum/match_inbound_reply.py`
- `~/work/py-hbs-ads/scripts/notion_scrum/plan_notion_update.py`
- `~/work/py-hbs-ads/scripts/notion_scrum/apply_notion_update.py`
- `~/work/py-hbs-ads/scripts/notion_scrum/scrum_state_doctor.py`

---

## 5. Skill responsibilities

The skill is responsible for:
- protocol
- prompting style
- safety rules
- decision boundaries
- ordering of script usage

The skill is **not** responsible for:
- being the durable storage layer
- doing identity resolution from raw text only
- freehand task correlation when structured state is available
- bypassing safe-write checks for convenience

---

## 6. Behavioral rules

### 6.1 Always anchor follow-up questions to a concrete task/project
When Hermes asks a human for clarification, it must include:
- project title
- task title if applicable
- what is missing
- what reply would resolve it

Bad:
- “Mày confirm giúp tao nhé?”

Good:
- “@Ma — task `rough cut v1` của project `Game teaser 03`: hiện chưa có due date. Mày muốn để ngày nào?”

### 6.2 Prefer explicit targeted asks
When possible, Hermes should target one person explicitly.

Good:
- “@Duc — task `export package` đang blocked vì thiếu asset hay đang chỉ chờ review?”

This reduces ambiguity during reply matching.

### 6.3 Record every outbound Scrum question
If Hermes asks a question that may later trigger a Notion update, it should record it in the pending prompt ledger.

That means using `record_pending_prompt.py` after sending or preparing the question content.

### 6.4 Resolve identity by platform user ID, not display name
Display name is only a convenience signal.
The authoritative key is:
- platform + platform user ID

Hermes must not rely on nickname text alone when deciding who replied.

### 6.5 Use scripts before deciding on a write
For inbound replies that may change Notion state, Hermes should use scripts in this order:
1. `resolve_person.py`
2. `match_inbound_reply.py`
3. `plan_notion_update.py`
4. `apply_notion_update.py` only if the plan is safe and sufficiently confident

### 6.6 Ambiguity must stop writes
If identity, target, or intent is ambiguous:
- do **not** write to Notion
- ask a clarifying follow-up in the thread
- preserve the unresolved state

### 6.7 Narrow V1 write surface
In V1, Hermes may only auto-write a small set of update types:
- blocker note
- owner acknowledgment
- short status note
- due-date proposal/note
- page comment or discussion summary
- pending question answered marker

It must **not** auto-write in V1 for:
- reassignment without explicit confirmation
- completion claims inferred from casual chat
- project-level completion claims inferred from one person’s reply
- new task creation from vague discussion

---

## 7. Outbound question protocol

When Hermes needs follow-up information:

1. Determine the target task/project.
2. Determine the intended target human if possible.
3. Phrase the question explicitly.
4. Ask for one of a small set of answer shapes.
5. Record the prompt in the local pending ledger.

Preferred answer shapes:
- date
- status choice
- blocked/not blocked
- short note
- yes/no acknowledgment

Preferred question examples:
- “@Ma — task `rough cut v1`: due date mày muốn để ngày nào? Trả lời theo dạng `YYYY-MM-DD` giúp tao.”
- “@Duc — task `VO handoff`: đang `blocked`, `in progress`, hay `waiting review`?”
- “@Toàn — project `B1` chưa có task breakdown. Mày muốn chia thành 2–3 output nào trước?”

---

## 8. Inbound reply protocol

When a human replies in the thread and the reply may affect Notion state:

1. Read the message normally.
2. Resolve sender using the local registry.
3. Try to match the reply to an open pending prompt.
4. If matched confidently, plan the update.
5. If the update is allowed, apply it.
6. If confidence is insufficient, ask a clarifying question.

The skill must prefer deterministic matching over pure conversational inference.

---

## 9. Matching rules the skill should assume

The skill should assume the external matcher uses this priority order:
1. explicit reply-to a known Hermes question message
2. same thread + same sender + exactly one open prompt for that sender
3. explicit task/project reference in the text
4. same thread + exactly one open prompt total
5. otherwise ambiguous

The skill should not override that logic ad hoc.

---

## 10. Confidence policy

The skill should treat a write as safe only when all are true:
- sender identity resolved by platform user ID
- pending prompt matched uniquely or near-uniquely
- update type is in the V1 allowlist
- the planned write is small and specific

When one of those fails, Hermes must not “just do the reasonable thing.”
It must ask.

---

## 11. Tone and response style

The skill should make Hermes sound like a practical Scrum/traffic manager:
- direct
- concise
- task-anchored
- owner-aware
- low-drama

It should avoid:
- vague prompts
- long managerial speeches
- pretending confidence when the mapping is unclear
- hidden Notion writes without surfacing what changed

Good default structure for follow-up:
1. target person
2. task/project anchor
3. exact question
4. preferred answer format

Good default structure for applied updates:
1. what was understood
2. what was updated in Notion
3. what still remains unclear, if anything

---

## 12. Required transparency on writes

When Hermes writes to Notion in this workflow, it should usually say so briefly in-thread unless the user explicitly prefers silent updates.

Example:
- “OK, tao ghi note blocked vào task `VO handoff` rồi: thiếu asset từ client.”
- “Tao chưa update do chưa rõ mày đang nói task `rough cut v1` hay `export package`.”

This helps human trust and auditability.

---

## 13. Failure handling

If a helper script fails:
- do not fall back to unsafe freehand updates
- explain the failure briefly
- keep the human-facing question/response flow moving if possible
- suggest the next safe action

Examples:
- identity registry missing
- pending prompt file malformed
- Notion API unavailable
- target task/page no longer exists

In such cases Hermes should degrade to:
- conversational clarification
- no write
- clear explanation

---

## 14. Recommended channel binding usage

This skill should be attached via Discord channel binding or equivalent scope control.

Why:
- avoids polluting unrelated channels with Scrum behavior
- keeps the protocol local to the intended workstream
- allows custom channel prompt text to reinforce the operating rules

Recommended pairing:
- one channel prompt for role framing
- one bound skill for detailed behavior

---

## 15. Minimal acceptance criteria for this skill

The skill is acceptable when it causes Hermes to:
- always anchor follow-up to a task/project
- always use person resolution before attribution-sensitive writes
- always consult the pending prompt ledger before task correlation
- never auto-write on ambiguity
- keep the public-thread UX readable and lightweight

---

## 16. Future upgrade path

If this protocol proves useful, parts may later graduate into Hermes core.
But V1 should remain external.

Potential later candidates for core support:
- structured sender metadata persistence in transcripts
- first-class pending prompt correlation hooks
- participant-aware thread memories

Until then, this skill should assume those concerns are handled by scripts and local state.

---

## 17. v3.0 Staffing-Awareness

### 17.1 Three-Layer State Model

v3.0 introduces a three-layer state model for managing identity, coordination, and staffing information:

| Layer | File | Role | Mutability |
|---|---|---|---|
| **Identity** | `team_registry.json` | Canonical person keys, aliases, platform identities (Discord user IDs, display names), Notion mappings | Static — operator-edited |
| **Coordination** | `pending_prompts.json` | Outbound messages awaiting reply | Transient — written/cleared by scripts |
| **Staffing** | `people_state.json` | Leave status, availability, backup routing targets, bandwidth facts | Short-horizon operational — written by `update_people_state.py` |

**Critical assignment boundary:** Assignments (task owners, project owners) are derived from `board_snapshot.json` + `team_registry.json`. They are **never** manually entered in `people_state.json`. The staffing layer records operational availability facts only — not ownership.

A fourth runtime artifact — `cache/staffing_snapshot.json` — is produced by `build_staffing_snapshot.py` as a derived merge of `people_state.json`, `board_snapshot.json`, and `team_registry.json`. This is a cache artifact, not an operator-maintained file.

### 17.2 Staffing-Aware Coordination Goals

When `staffing_snapshot.json` is present and fresh, Hermes's coordination goals extend beyond the base protocol to include:

- **Absent owner detection:** Identify tasks and projects whose owners are on leave or OOO, and surface the configured backup contact.
- **Overload flagging:** Flag owners where `active_projects >= 3` OR `active_tasks >= 8` as overloaded. Mention overload context when routing follow-ups.
- **Availability-aware routing:** Ensure follow-up messages reach the person who can actually act on them, not just the static Notion owner. Routing changes the follow-up target only — Notion task or project ownership is never auto-mutated.

Staffing awareness is **conditional**: when `staffing_snapshot.json` is absent or stale, the skill falls back to board-only mode (see §17.5).

### 17.3 Operator Commands for Leave and Availability

> **Safety rule:** All writes require `--execute`. The default mode is **dry-run**. Always review dry-run output before passing `--execute`.

**Write-path commands (`update_people_state.py`):**

```
# Record leave period with optional backup routing and note
update_people_state.py --person <alias> --action set_leave --until YYYY-MM-DD [--backup <alias>] [--note "..."] [--execute]

# Clear leave status (returns person to active)
update_people_state.py --person <alias> --action clear_leave [--execute]

# Set bandwidth level (reduced | limited | normal)
update_people_state.py --person <alias> --action set_bandwidth --bandwidth reduced|limited|normal [--execute]

# Set standing backup routing target
update_people_state.py --person <alias> --action set_backup --backup <alias> [--execute]
```

**Read-path commands (`query_people_state.py` — no preflight required, always read-only):**

```
# Show staffing facts for a specific person
query_people_state.py --person <alias>

# List everyone currently on leave as of today
query_people_state.py --on-leave-today

# List everyone with reduced bandwidth
query_people_state.py --reduced-bandwidth

# Show who is configured as backup for a given person
query_people_state.py --backup-for <alias>
```

All `<alias>` values must be canonical person keys validated against `team_registry.json`. Unrecognized aliases are rejected with a validation error.

### 17.4 Routing Rules for Absent Owners

When a follow-up needs to reach a task or project owner, apply this routing decision table:

| `availability.status` | backup configured | Routing outcome |
|---|---|---|
| `active` | yes or no | Route to owner directly |
| `leave` | yes | Route to backup |
| `leave` | no | Surface escalation-needed signal |
| `ooo` | yes | Route to backup |
| `ooo` | no | Surface escalation-needed signal |
| `unknown` | yes or no | Block and prompt operator |

**Backup field disambiguation:**
- `availability.backup_person_key` — leave-specific backup, set when a leave record is written.
- `coordination.backup_person_key` — standing policy-level routing target, set independently.

Both fields hold canonical person keys validated against `team_registry.json`. When a leave record is present and has its own backup, prefer `availability.backup_person_key`; fall back to `coordination.backup_person_key` if the leave-specific field is absent.

No routing action modifies Notion task or project ownership. Routing affects follow-up message targets and daily report action lines only — changes are recommendations and prompts, not ownership mutations.

### 17.5 Daily Report Expectations with Staffing Risk

**When `staffing_snapshot.json` is present and fresh**, the daily board report includes the following staffing sections:

- People currently on leave or with unusual availability (OOO, unknown status)
- Tasks with absent owners (owner on leave or OOO)
- Projects with absent owners and no backup configured (no-coverage risk)
- Overloaded owners (active_projects >= 3 OR active_tasks >= 8)
- Action lines for absent-owner items reference the backup person using their registry Discord mention token when a backup exists

The five staffing risk categories detected by the risk module:

1. Tasks assigned to absent owners
2. Projects whose owners are on leave
3. Absent owners with no backup configured
4. Overloaded owners (active_projects >= 3 OR active_tasks >= 8)
5. Reduced-bandwidth owners carrying overdue items

**When `staffing_snapshot.json` is absent or stale**, the report falls back to **board-only mode**:

- A warning note is included in the report indicating that staffing data is unavailable or outdated
- All staffing sections are skipped
- Routing decisions proceed as if all owners are available

Board-only mode is a valid operational state — not an error. Hermes should not refuse to run a daily report just because staffing data is missing. The board-only report is still a complete and useful output.
