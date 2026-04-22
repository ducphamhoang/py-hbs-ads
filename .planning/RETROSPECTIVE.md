# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2.0 — Hermes Discord Notion Scrum Level 2+3

**Shipped:** 2026-04-22  
**Phases:** 3 | **Plans:** 10 | **Sessions:** 1

### What Was Built

- Typed Notion Scrum workflow dataclasses for inbound events, prompt records, match results, and update plans.
- Shared person-resolution, prompt lifecycle, and audit modules.
- Thin wrappers for the existing Level 1 scripts.
- Stable result envelopes and a Notion adapter boundary.
- Operator entrypoints for pending prompt creation, inbound reply processing, and preflight.
- Reusable shared-thread attributed automation documentation and focused tests.

### What Worked

- Building shared modules before entrypoints kept the Level 3 commands small and testable.
- Stable JSON result contracts made dry-run and execute behavior easy to compare.
- Local-only runtime state plus sanitized fixtures gave useful examples without committing live Discord/Notion data.

### What Was Inefficient

- Some legacy planning state from Phase 7 and old quick tasks had to be reconciled during milestone close.
- The GSD SDK milestone wrapper did not handle `gsd-sdk query milestone.complete` correctly in this environment; the underlying `gsd-tools.cjs milestone complete` path worked.

### Patterns Established

- Shared-thread attributed automation: resolve actor, anchor prompt, match reply, plan narrow update, apply through adapter, audit every step.
- Write-capable commands default to dry-run and require explicit execute mode.
- Real runtime state stays local-only; committed files are docs, examples, and tests.

### Key Lessons

1. Attribution-sensitive automations need explicit identity resolution before any write path.
2. Adapter boundaries are worth adding early when the generic workflow may be reused with another backend.
3. Milestone close should include an open-artifact audit before archiving, because stale local GSD artifacts can outlive the actual work.

### Cost Observations

- Model mix: not measured.
- Sessions: 1 closing session after autonomous phase execution.
- Notable: focused tests plus a runnable sample flow caught a portability bug in the sample runner before close.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v2.0 | 1 | 3 | Moved from one-off Hermes scripts to shared modules, stable entrypoints, and archived runtime-state policy |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v2.0 | 80 passing | Focused module and entrypoint coverage | Shared Notion Scrum modules, samples, and docs |

### Top Lessons

1. Keep source examples sanitized and operational state local.
2. Test the runnable operator flow, not only individual helpers.
