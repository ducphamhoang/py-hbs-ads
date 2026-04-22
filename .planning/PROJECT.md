# py-hbs-ads

## Current State

**Shipped milestone:** v2.0 Hermes Discord ↔ Notion Scrum Level 2+3  
**Shipped date:** 2026-04-22  
**Current focus:** Between milestones; ready for `$gsd-new-milestone`.

v2.0 delivered the Hermes Discord ↔ Notion Scrum workflow as a reusable attributed-automation pattern:

- Shared Level 2 modules for workflow models, person resolution, prompt lifecycle, and audit events.
- Level 3 operator entrypoints for pending prompt creation, inbound reply processing, and preflight validation.
- Stable JSON result contracts and explicit dry-run/execute behavior for write-capable flows.
- A Notion adapter boundary separating domain writes from generic attribution, matching, and audit logic.
- Pattern documentation and tests covering shared modules and entrypoint pipelines.

## What This Is

`py-hbs-ads` is a Python rewrite of the `hbs-ads` ad-operations CLI and a home for adjacent operator automation used by internal teams and AI agents. It keeps the ad-production command surface maintainable while adding safe, auditable workflow automation around shared operational channels.

## Core Value

Provide one maintainable Python CLI and automation contract for ad-production operations without regressing operational clarity, safety, attribution, or migration practicality.

## Requirements

### Validated

- ✓ Python CLI named `hbs-ads` with the documented command tree and thin command handlers — v1.0
- ✓ Compatibility with the current workspace structure, config model, and key workflow inputs where practical — v1.0
- ✓ Feature-first Python architecture that keeps workflow logic local and side effects explicit — v1.0
- ✓ Incremental migration path for critical legacy workflows — v1.0
- ✓ Hermes shared workflow modules for models, prompt state, person resolution, and audit — v2.0
- ✓ Hermes operator entrypoints with stable JSON envelopes and dry-run/execute discipline — v2.0
- ✓ Notion adapter boundary for attributed automation — v2.0
- ✓ Reusable shared-thread attributed automation documentation and tests — v2.0

### Active

No active milestone requirements are currently defined. The next milestone should be created with `$gsd-new-milestone`.

### Out of Scope

- GUI or dashboard delivery unless a future milestone explicitly prioritizes it.
- Replacing `ffmpeg` and `ffprobe` with native media processing.
- Redesigning creative strategy, taxonomy, or the operational workflow itself.
- Big-bang cutover from the legacy repo; migration remains incremental and testable.
- Free-form autonomous mutation without explicit prompt/state anchors.
- Broad write access beyond narrow, audited allowlists.

## Context

The repo now has two shipped planning arcs:

- v1.0 established the Python rewrite foundation and core CLI workflows.
- v2.0 added the Hermes Discord ↔ Notion Scrum automation pattern on top of the same safety principles: explicit state, attribution before mutation, dry-run defaults, and testable adapters.

Live runtime state for Hermes remains local-only under `state/notion_scrum/`; the repo keeps sanitized examples and operator documentation instead of committing real Discord/Notion IDs or audit history.

Legacy SharePoint live-auth work was archived as a legacy backlog item and is not part of the completed Hermes v2.0 PRD path.

## Constraints

- **Language:** Python remains the required implementation language.
- **Architecture:** Feature-first structure from `docs/architecture.md` remains the default.
- **Compatibility:** Existing workspace layout and key configs should be preserved where practical.
- **Dependencies:** `ffmpeg`, `ffprobe`, SQLite, SharePoint auth, AI providers, Notion, Discord, and webhook integrations remain external dependencies by design.
- **Operational safety:** Dry-run behavior, explicit side effects, state preflight, and audit trails remain mandatory for mutating workflows.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep the `hbs-ads` CLI contract while changing implementation language to Python | Preserves operator and agent discoverability while allowing a more maintainable codebase for this rewrite | ✓ Good |
| Use `src/hbs_ads/{cli,app,core,infra,features}` as the top-level application layout | Keeps feature logic cohesive and prevents Python utility sprawl | ✓ Good |
| Build the rewrite incrementally from foundations to workflow migration instead of wrapper-first parity | Reduces long-term technical debt and gives each phase a clean architectural target | ✓ Good |
| Treat the old `~/work/hbs-ads` repo as the product and workflow reference, not as code to port mechanically | Preserves intent while allowing cleaner Python internals | ✓ Good |
| Consolidate Hermes Level 1 scripts behind shared modules before building operator entrypoints | Avoids duplicated identity, prompt, and audit logic | ✓ Good |
| Keep Notion-specific behavior behind an adapter boundary | Allows the attributed-automation pattern to be reused with another backend later | ✓ Good |
| Keep live Hermes runtime state local-only and commit only sanitized templates | Prevents Discord/Notion identifiers, emails, and operational audit history from leaking into source control | ✓ Good |
| Archive legacy SharePoint live-auth work outside active roadmap routing | Keeps the Hermes PRD path complete without reviving unrelated legacy scope | ✓ Good |

## Next Milestone Goals

To be defined by `$gsd-new-milestone`.

Candidate areas to consider:

- Production rehearsal and hardening for Hermes/Notion live operation.
- A second backend implementation to prove the attributed-automation pattern generalizes.
- Formal cutover or packaging work for operator adoption.

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-04-22 after v2.0 milestone*
