# Milestones

## v3.0 Staffing-Aware Discord↔Notion Scrum (Shipped: 2026-04-29)

**Phases completed:** 6 phases, 16 plans, 58 tasks

**Archived:**

- `.planning/milestones/v3.0-ROADMAP.md`
- `.planning/milestones/v3.0-REQUIREMENTS.md`

**Key accomplishments:**

- People-state schema with centralized validated store module supporting load/save/transitions
- Staffing snapshot derived from team registry + board cache + people state with effective owner mapping
- Preflight extended with people-state integrity checks (schema validation, backup key validation, date window validation)
- Staffing risk detection covering 5 categories: absent owners, projects with absent owners, no-backup escalation, overloaded owners, reduced-bandwidth with overdue
- Daily board report extended with staffing-aware sections (leave status, risk highlights, backup-aware action lines)
- Backward compatibility preserved: board-only report continues to work without people_state.json present
- Follow-up routing that respects leave/backup configurations while preserving Notion ownership integrity
- Three-layer state model documented and skill coverage updated (AGENT_CAPABILITIES.md, Hermes Discord↔Notion Scrum skill)
- All 38 v3.0 requirements validated and complete

---

## v2.0 Hermes Discord Notion Scrum Level 2+3 (Shipped: 2026-04-22)

**Phases completed:** 3 phases, 10 plans, 13 tasks

**Archived:**

- `.planning/milestones/v2.0-ROADMAP.md`
- `.planning/milestones/v2.0-REQUIREMENTS.md`
- `.planning/milestones/v2.0-phases/`

**Known legacy scope:** SharePoint live-auth/search/download/upload remains archived outside active routing at `.planning/archive/legacy/999.1-live-sharepoint-authentication-and-remote-transfer.md`.

**Key accomplishments:**

- Typed Notion scrum workflow dataclasses for inbound events, prompt records, match results, and update plans
- Pure person-resolution helpers for canonical identity lookup and actor label formatting
- Enum-constrained audit events with centralized JSONL append helpers
- Canonical prompt lifecycle store with open-prompt filtering, transitions, and schema validation
- Notion scrum scripts refactored into thin wrappers over shared identity, prompt, and audit modules
- Stable result envelopes and Notion adapter boundary for Level 3 operator entrypoints
- Validated create_pending_prompt entrypoint with audit and stable JSON output
- End-to-end inbound reply pipeline with dry-run default, execute mode, and clarification fallback
- Operational preflight entrypoint for registry, prompt, duplicate ID, and unresolved mapping checks
- Reusable shared-thread attributed automation guide with expanded module and entrypoint coverage

---
