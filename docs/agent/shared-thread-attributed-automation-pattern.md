# Shared-Thread Attributed Automation Pattern

This document describes the reusable pattern behind the Hermes Discord <-> Notion Scrum workflow.
The pattern lets an assistant participate in one shared human thread while using deterministic local state to decide whether a side effect is safe.

The first implementation is Notion Scrum, but the pattern is broader than Notion.

## Pattern Summary

Shared-thread attributed automation applies when:

- multiple humans can reply in one shared channel or thread,
- a model can understand the conversation but cannot safely infer attribution from text alone,
- an external system can be updated only after sender, target, and intent are known,
- ambiguity should produce a clarifying question rather than a write.

The core loop is:

1. Resolve the sender from runtime metadata.
2. Match the message to a durable pending prompt.
3. Plan a narrow update from the prompt's allowed action surface.
4. Apply the update only when the plan is safe and execute mode is explicit.
5. Append audit records for attempts and outcomes.
6. Return a stable result envelope so operators and future automation can reason over the outcome.

## Generic Components

These pieces are reusable across backends such as Notion, Linear, Teams, or another task system.

### Sender Resolution

Use platform runtime identifiers as the authority:

- `platform`
- `platform_user_id`
- a local `identity_index`
- a canonical person record

Display names are useful for comments and logs, but they are not identity.

Current implementation:

- `scripts/notion_scrum/person_resolution.py`
- `state/notion_scrum/team_registry.json`

### Pending Prompt Lifecycle

Every outbound question that can later trigger a write must become a durable prompt object.
The prompt records:

- thread and channel anchors,
- target person,
- task or project target,
- outbound message ID and text,
- allowed update types,
- lifecycle status.

Current implementation:

- `scripts/notion_scrum/prompt_store.py`
- `scripts/notion_scrum/create_pending_prompt.py`
- `state/notion_scrum/pending_prompts.json`

### Matching

Inbound replies are matched deterministically. Strong signals include reply-to message IDs, same thread, sender matching target, and explicit task/project references.

The system should prefer false negatives over false positive writes. If there is no confident match, the result must require clarification.

Current implementation:

- `scripts/notion_scrum/match_inbound_reply.py`
- `scripts/notion_scrum/process_inbound_reply.py`

### Planning

The planner converts matched human text into a narrow update type and value. It must respect the prompt's `allowed_update_types`.

Safe update planning is separate from live mutation.

Current implementation:

- `scripts/notion_scrum/plan_notion_update.py`

### Stable Result Envelopes

Operator entrypoints return a stable top-level shape:

- `ok`
- `action_taken`
- `write_applied`
- `requires_clarification`
- `clarification_reason`
- `pending_prompt_id`
- `canonical_person_key`
- `matched_prompt_id`
- `resolved_update_type`
- `audit_events`
- `errors`
- `data`

Dry-run and execute results use the same keys.

Current implementation:

- `scripts/notion_scrum/result_contracts.py`

### Audit Discipline

Audit records are append-only JSONL events. Event names are enum-backed so scripts do not invent ad hoc event strings.

Current implementation:

- `scripts/notion_scrum/audit.py`
- `state/notion_scrum/audit_log.jsonl`

## Notion-Specific Components

These pieces are specific to the current reference backend and should be replaced or adapted for another backend.

- Mapping canonical people to Notion users or people pages.
- Translating update plans into Notion comments or page property patches.
- Knowing whether a Notion target is a task or project page.
- Calling the Notion API.

Current implementation:

- `scripts/notion_scrum/notion_adapter.py`
- `scripts/notion_scrum/apply_notion_update.py`
- `scripts/notion_scrum/lookup_notion_person.py`

New generic orchestration should call the adapter, not raw Notion API helpers.

## Entrypoints

The Level 3 operator surface is:

- `create_pending_prompt.py` - validate and record an outbound prompt.
- `process_inbound_reply.py` - resolve, match, plan, and dry-run or execute an update.
- `preflight.py` - validate local registry and prompt state.

Low-level scripts remain useful for debugging, but routine operation should use the Level 3 entrypoints.

## Safety Invariants

These invariants are the reason the pattern is safe enough for shared threads:

- Never rely on display name for identity-sensitive writes.
- Never write when sender identity is unresolved.
- Never write when a reply cannot be matched confidently to a pending prompt.
- Never write an update type outside the prompt's allowlist.
- Dry-run is the default for write-capable flows.
- Execute mode must be explicit.
- A prompt can be marked answered only after a successful live write.
- Ambiguity returns `requires_clarification=true`.
- Audit records are append-only.

## Adopting The Pattern For Another Backend

To adapt this workflow:

1. Keep sender resolution, prompt store, matching, planning, audit, and result contracts generic.
2. Define the backend-specific target schema in each prompt's domain section.
3. Create a backend adapter with action planning and apply functions.
4. Keep the write allowlist narrow.
5. Add a preflight check for backend-specific mapping or credential assumptions.
6. Add tests for dry-run, execute, ambiguity, and invalid state.
7. Document what is generic and what belongs to the backend adapter.

Do not move this into Hermes core until at least two backend implementations prove the abstraction boundary.

## Current Reference Map

```text
scripts/notion_scrum/
  models.py                  # shared data contracts
  person_resolution.py       # generic identity resolution
  prompt_store.py            # generic pending prompt lifecycle
  audit.py                   # generic audit events
  result_contracts.py        # generic operator result envelope
  match_inbound_reply.py     # generic-ish reply matcher
  plan_notion_update.py      # Notion Scrum update planner
  notion_adapter.py          # Notion adapter boundary
  apply_notion_update.py     # Notion write implementation
  create_pending_prompt.py   # Level 3 outbound prompt entrypoint
  process_inbound_reply.py   # Level 3 inbound reply entrypoint
  preflight.py               # Level 3 state health check
```
