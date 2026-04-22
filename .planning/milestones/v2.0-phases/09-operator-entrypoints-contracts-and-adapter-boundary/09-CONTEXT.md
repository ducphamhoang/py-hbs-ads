# Phase 09: Operator Entrypoints, Contracts, and Adapter Boundary - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Source:** PRD Express Path (`docs/agent/hermes-discord-notion-scrum-prd-2026-04-20.md`)

<domain>
## Phase Boundary

Phase 09 productizes the Hermes Discord <-> Notion Scrum Level 3 workflow. Phase 08 already created the shared Level 2 modules. Phase 09 must add operator-facing entrypoints, stable JSON result envelopes, dry-run/execute discipline, and a clear Notion adapter boundary.

Old Phase 7 SharePoint work was checked against the Hermes PRD on 2026-04-22 and is unrelated to this PRD. It remains deferred and must not block Phase 09 planning.
</domain>

<decisions>
## Implementation Decisions

### Entrypoints
- `scripts/notion_scrum/process_inbound_reply.py` is the one-command inbound flow for resolve -> match -> plan -> apply-or-clarify.
- `scripts/notion_scrum/create_pending_prompt.py` is the one-command prompt recording flow with validation and audit output.
- `scripts/notion_scrum/preflight.py` is the one-command operational health check.

### Stable Result Contracts
- Every Level 3 entrypoint returns a stable JSON envelope containing at least `ok`, `action_taken`, `write_applied`, `requires_clarification`, `clarification_reason`, `pending_prompt_id`, `canonical_person_key`, `matched_prompt_id`, `resolved_update_type`, `audit_events`, and `errors`.
- Dry-run and execute modes must return the same top-level envelope shape.
- Write-capable commands default to dry-run and require `--execute` for live mutation.

### Safety
- Ambiguous sender, target, or update intent must stop writes.
- `prompt.answered` must never be set in dry-run.
- Prompt closure can happen only after successful live write.

### Adapter Boundary
- Notion-specific behavior belongs behind `scripts/notion_scrum/notion_adapter.py`.
- Generic orchestration code may compose prompt, identity, match, plan, and adapter calls but must not call raw Notion patch helpers or encode Notion API details directly.

### the agent's Discretion
- Exact helper function names and test organization are flexible as long as public entrypoints and stable JSON output are preserved.
- The implementation may keep existing low-level scripts usable for debugging.
</decisions>

<canonical_refs>
## Canonical References

### Product Requirements
- `docs/agent/hermes-discord-notion-scrum-prd-2026-04-20.md` - Level 3 deliverables, result envelope, dry-run/execute contract, adapter boundary.
- `docs/agent/hermes-discord-notion-scrum-skill-spec.md` - Skill behavior, write safety, failure handling, user-facing workflow expectations.
- `docs/agent/hermes-discord-notion-scrum-state-schema.md` - Team registry, pending prompt, and audit log schemas.

### Existing Implementation
- `scripts/notion_scrum/models.py` - Shared workflow dataclasses from Phase 08.
- `scripts/notion_scrum/person_resolution.py` - Shared identity and actor label helpers from Phase 08.
- `scripts/notion_scrum/prompt_store.py` - Shared prompt lifecycle helpers from Phase 08.
- `scripts/notion_scrum/audit.py` - Shared audit event helpers from Phase 08.
- `scripts/notion_scrum/match_inbound_reply.py` - Existing reply matcher.
- `scripts/notion_scrum/plan_notion_update.py` - Existing update planner.
- `scripts/notion_scrum/apply_notion_update.py` - Existing Notion write executor to isolate behind the adapter.
- `tests/test_notion_scrum.py` - Current behavior tests to preserve.
</canonical_refs>

<specifics>
## Specific Ideas

- Result envelope helper should reduce duplicated JSON response construction across the three entrypoints.
- `process_inbound_reply.py` should accept stdin payloads shaped like `{"event": {...}}` and support path flags for registry, prompt state, and audit log.
- `create_pending_prompt.py` should accept a prompt object on stdin, validate it using `prompt_store.validate_prompt_schema`, append only on valid input, and return validation errors otherwise.
- `preflight.py` should combine registry checks, prompt checks, unresolved Notion mapping reporting, duplicate prompt ID detection, and existing doctor-style warnings.
</specifics>

<deferred>
## Deferred Ideas

- Full pattern-level documentation belongs to Phase 10.
- Broad test coverage across all modules and pipelines belongs to Phase 10, though Phase 09 plans include focused tests for new entrypoint contracts.
- SharePoint live auth/search/download/upload remains deferred outside the Hermes Discord <-> Notion Scrum PRD path.
</deferred>

---

*Phase: 09-operator-entrypoints-contracts-and-adapter-boundary*
*Context gathered: 2026-04-22 via PRD Express Path*
