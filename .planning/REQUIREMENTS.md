# Requirements: py-hbs-ads

**Defined:** 2026-04-07
**Core Value:** Provide one maintainable Python CLI contract for the ad-production workflow without regressing operational clarity, safety, or migration practicality.

---

## Milestone v1.0 Requirements (Complete)

### Foundations

- [x] **FOUND-01**: The repo has a Python package layout with `src/hbs_ads` and a documented developer toolchain.
- [x] **FOUND-02**: The CLI entrypoint exposes the documented command groups with discoverable help output.
- [x] **FOUND-03**: Shared runtime concerns are centralized for config, output, errors, and logging.
- [x] **FOUND-04**: Feature services use typed request and result models instead of loose dict passing.
- [x] **FOUND-05**: Mutating workflows support an explicit `dry_run` request path where practical.

### Workspace And Config

- [x] **BOOT-01**: Operator can initialize a workspace structure compatible with the rewrite expectations.
- [x] **BOOT-02**: Operator can load config from file, env, and CLI overrides with predictable precedence.
- [x] **BOOT-03**: Workspace path resolution is centralized and reusable across features.
- [x] **BOOT-04**: Local SQLite setup and migrations are available behind an explicit application boundary.

### Core Workflow Migration

- [x] **INGEST-01**: Operator can run `hbs-ads ingest run` against a workspace with explicit dry-run support.
- [x] **TRIM-01**: Operator can run `hbs-ads trim run` from config and `hbs-ads trim clip` from direct flags.
- [x] **TAG-01**: Operator can run `hbs-ads tag auto`, `ai`, `approve`, and `pending`.
- [x] **VAR-01**: Operator can run `hbs-ads variants generate`, `assemble`, `export`, `validate`, and `archive`.
- [x] **HOOK-01**: Operator can run `hbs-ads hooks assemble`.
- [x] **PIPE-01**: Operator can run `hbs-ads pipeline run` for the common orchestrated path.

### External Integrations

- [x] **SHARE-01**: Operator can run `hbs-ads sharepoint transfer` with file-backed stub auth.
- [x] **COMP-01**: Operator can run `hbs-ads competitor run` to produce a competitor report.
- [x] **PERF-01**: Operator can run `hbs-ads perf run` to produce a performance report.
- [x] **NOTIFY-01**: Operator can run `hbs-ads notify send` to dispatch a webhook notification.
- [x] **VOICE-01**: Operator can run `hbs-ads voiceover generate` to produce AI voiceover output.

### Quality and Cutover

- [x] **QUAL-01**: Output contracts (schemas, file paths, result shapes) are documented and tested.
- [x] **QUAL-02**: Parity smoke tests exercise representative legacy-style inputs against the Python rewrite.
- [x] **QUAL-03**: Module entrypoints are verified callable from outside the package boundary.
- [x] **MIG-01**: Migration and cutover documentation describes the incremental path from Go to Python for operators.

### SharePoint Live Auth (Phase 7 — Not Started)

- [ ] **SHARE-02**: Operator can authenticate to SharePoint with real credentials (MSAL or equivalent).
- [ ] **SHARE-03**: Operator can search and list remote SharePoint assets.
- [ ] **SHARE-04**: Operator can download files from SharePoint to a local workspace.
- [ ] **SHARE-05**: Operator can upload files from a local workspace to a SharePoint target.

---

## Milestone v2.0 Requirements — Hermes Discord ↔ Notion Scrum Level 2+3

**Milestone goal:** Refactor the existing Level 1 Discord/Notion Scrum script pile into a coherent, productized Level 3 pattern.

### MODULES — Shared workflow modules (Level 2)

- [x] **MOD-01**: System has a shared `models.py` with typed workflow objects: `InboundEvent`, `PromptRecord`, `MatchResult`, `UpdatePlan`.
- [x] **MOD-02**: System has a shared `person_resolution.py` owning platform identity resolution, canonical-person lookup, pending-person candidate surfacing, and actor label generation.
- [x] **MOD-03**: System has a shared `prompt_store.py` owning the full prompt lifecycle (load, save, append, retrieve open, mark answered/cancelled/expired, validate schema).
- [x] **MOD-04**: System has a shared `audit.py` owning audit event formatting, append-only writes, and event-type conventions.
- [x] **MOD-05**: Existing scripts (`resolve_person.py`, `lookup_notion_person.py`, `record_pending_prompt.py`) become thin wrappers over the shared modules with no duplicated logic.

### ENTRY — Operator entrypoints (Level 3)

- [x] **ENTRY-01**: Operator can run `process_inbound_reply.py` to execute the full inbound pipeline (resolve → match → plan → apply) with a single command.
- [x] **ENTRY-02**: Operator can run `create_pending_prompt.py` to record a pending workflow object with validation and audit write in one command.
- [x] **ENTRY-03**: Operator can run `preflight.py` to validate registry integrity, prompt integrity, unresolved people, duplicate IDs, and state consistency in one command.
- [x] **ENTRY-04**: Every write-capable entrypoint supports explicit dry-run (default) and execute modes with identical output shape in both modes.

### CONTRACT — Stable result contracts

- [x] **CONTRACT-01**: Every Level 3 entrypoint returns a stable JSON result envelope with fields: `ok`, `action_taken`, `write_applied`, `requires_clarification`, `clarification_reason`, `pending_prompt_id`, `canonical_person_key`, `matched_prompt_id`, `resolved_update_type`, `audit_events`.
- [x] **CONTRACT-02**: Prompt is marked answered only after a successful live write — never in dry-run mode.

### ADAPTER — Domain adapter boundary

- [x] **ADAPTER-01**: Notion-specific code (user-ID mapping, page/comment patch calls, task semantics) is isolated from generic pattern code (sender resolution, prompt lifecycle, reply matching, audit discipline) so a future backend can be substituted without rewriting the foundation.

### DOCS — Pattern documentation

- [x] **DOCS-01**: Documentation describes the general "shared-thread attributed automation" pattern — what is reusable across domains, what is Notion-specific, and how a future workflow can adopt the pattern.

### TEST — Test coverage

- [x] **TEST-01**: Tests cover all shared modules (models, prompt_store, person_resolution, audit) including edge cases and schema validation.
- [x] **TEST-02**: Tests cover entrypoint pipelines (inbound processing, prompt creation, preflight) in both dry-run and execute modes.

---

## Future Requirements (Deferred)

- Generalize the attributed-automation pattern to a second non-Notion backend (e.g. Linear, Teams) — deferred until reference impl is stable.
- Auto-expiry of pending prompts via scheduled job — deferred to after Level 3 ships.
- Real-time preflight dashboard — out of scope; CLI output is sufficient.

## Out of Scope

- Redesigning Hermes shared-session behavior or core transport — stays outside Hermes core by design.
- Free-form chat self-routing without explicit prompt/state anchors — safety constraint.
- Broader autonomous mutation beyond the narrow write allowlist — convenience pressure mitigation.
- Task creation from ambiguous discussion — too risky.

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 2 | Complete |
| BOOT-01 | Phase 2 | Complete |
| BOOT-02 | Phase 2 | Complete |
| BOOT-03 | Phase 2 | Complete |
| BOOT-04 | Phase 2 | Complete |
| INGEST-01 | Phase 3 | Complete |
| TRIM-01 | Phase 3 | Complete |
| TAG-01 | Phase 3 | Complete |
| VAR-01 | Phase 4 | Complete |
| HOOK-01 | Phase 4 | Complete |
| PIPE-01 | Phase 4 | Complete |
| SHARE-01 | Phase 5 | Complete |
| COMP-01 | Phase 5 | Complete |
| PERF-01 | Phase 5 | Complete |
| NOTIFY-01 | Phase 5 | Complete |
| VOICE-01 | Phase 5 | Complete |
| QUAL-01 | Phase 6 | Complete |
| QUAL-02 | Phase 6 | Complete |
| QUAL-03 | Phase 6 | Complete |
| MIG-01 | Phase 6 | Complete |
| SHARE-02 | Phase 7 | Pending |
| SHARE-03 | Phase 7 | Pending |
| SHARE-04 | Phase 7 | Pending |
| SHARE-05 | Phase 7 | Pending |
| MOD-01 | Phase 8 | Complete |
| MOD-02 | Phase 8 | Complete |
| MOD-03 | Phase 8 | Complete |
| MOD-04 | Phase 8 | Complete |
| MOD-05 | Phase 8 | Complete |
| ENTRY-01 | Phase 9 | Complete |
| ENTRY-02 | Phase 9 | Complete |
| ENTRY-03 | Phase 9 | Complete |
| ENTRY-04 | Phase 9 | Complete |
| CONTRACT-01 | Phase 9 | Complete |
| CONTRACT-02 | Phase 9 | Complete |
| ADAPTER-01 | Phase 9 | Complete |
| DOCS-01 | Phase 10 | Complete |
| TEST-01 | Phase 10 | Complete |
| TEST-02 | Phase 10 | Complete |
