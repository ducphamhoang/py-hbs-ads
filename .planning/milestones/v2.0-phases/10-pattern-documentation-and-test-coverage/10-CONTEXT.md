# Phase 10: Pattern Documentation and Test Coverage - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning
**Source:** ROADMAP + Hermes Discord <-> Notion Scrum PRD

<domain>
## Phase Boundary

Phase 10 closes the Hermes Discord <-> Notion Scrum Level 2+3 milestone by documenting the reusable shared-thread attributed automation pattern and expanding test coverage across the shared modules and Level 3 entrypoints.
</domain>

<decisions>
## Implementation Decisions

### Documentation
- Add a pattern-level document that clearly separates generic attributed-automation pieces from Notion-specific pieces.
- The document must explain how a future backend adopts the pattern without requiring Hermes core changes.

### Test Coverage
- Extend `tests/test_notion_scrum.py` rather than creating a separate suite, because the current workflow is still script-path based and all Notion scrum behavior is already covered there.
- Cover `models.py`, `prompt_store.py`, `person_resolution.py`, and `audit.py` edge cases.
- Cover all three Level 3 entrypoints with dry-run/execute or positive/negative output-shape assertions.

### the agent's Discretion
- Exact doc title and section names are flexible if the content satisfies the PRD and ROADMAP success criteria.
</decisions>

<canonical_refs>
## Canonical References

- `docs/agent/hermes-discord-notion-scrum-prd-2026-04-20.md` - Pattern and Level 3 acceptance criteria.
- `docs/agent/hermes-discord-notion-scrum-skill-spec.md` - Runtime behavior and safety rules.
- `docs/agent/hermes-discord-notion-scrum-state-schema.md` - State schema.
- `.planning/phases/08-shared-workflow-modules-level-2/*-SUMMARY.md` - Shared module implementation summaries.
- `.planning/phases/09-operator-entrypoints-contracts-and-adapter-boundary/*-SUMMARY.md` - Entry point implementation summaries.
</canonical_refs>

<specifics>
## Specific Ideas

- Suggested doc path: `docs/agent/shared-thread-attributed-automation-pattern.md`.
- Include a module map, adoption checklist, safety invariants, and backend adapter guide.
- Add tests for model defaults, prompt transitions, actor fallback order, audit enum/event values, and CLI-style result envelope parity.
</specifics>

<deferred>
## Deferred Ideas

- Extracting a generic package outside `scripts/notion_scrum` is deferred until there is a second backend.
- SharePoint live auth/search/download/upload remains outside this Hermes milestone path.
</deferred>

---

*Phase: 10-pattern-documentation-and-test-coverage*
*Context gathered: 2026-04-22*
