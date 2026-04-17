Workspace-local reference for Qwen workers
Source of truth: Hermes skill `qwen-code-standalone-headless`
Last synced by Hermes: 2026-04-09

Purpose
- Help the parent orchestrator delegate bounded tasks to standalone Qwen workers with minimal context pollution.

Core rules
- Use Qwen only for bounded tasks with explicit scope.
- Parent must provide exact task, inputs, must-read docs, allowed tools/APIs, must-not-do constraints, and output headings.
- Parent keeps cross-step planning, ambiguity handling, approval gates, and final synthesis.
- If Qwen returns a blocker or fails repeatedly, fall back to the main orchestrator/model instead of breaking the pipeline.

Turn budget notes
- max-session-turns is a turn budget, not a raw tool/API-call budget.
- One turn may still include multiple tool/API actions.
- Structured analysis workers often need about 2 turns.
- Bounded tool/API workers often need 2-4 turns.
- Heavier bounded workers may reasonably use 4-8 turns, or up to 10-15 as an upper bound.

Relevant templates
- generic-analysis-worker-prompt.md
- generic-tool-worker-prompt.md
- py-hbs-ads-video-worker-prompt.md
- notion-check-worker-prompt.md
- sample-py-hbs-ads-video-artifact-analysis.md
- sample-notion-project-status-worker.md

Relevant local reference
- video-analysis-mapping.md

py-hbs-ads video-specific reminders
- Distinguish workspace-local artifacts from shared-library artifacts.
- Prefer library-first lookup.
- If falling back from library to another trusted local source, say so explicitly.
- Do not default trim outputs to _ASSETS/trimmed without checking whether the target is workspace-local or reusable library output.
