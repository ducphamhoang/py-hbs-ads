# Orchestrator Agent Guide

This guide teaches a parent orchestrator how to coordinate the Python rewrite of `hbs-ads` using one parent plus bounded domain workers.

## Purpose

The orchestrator owns:

- intent resolution
- workspace and library path resolution
- stage ordering
- parent-side command execution for deterministic steps
- review gate preservation
- artifact verification
- deciding when to delegate and when to stop

The orchestrator should not behave like a passive dispatcher. It should directly execute mechanical steps and delegate only when domain reasoning or bounded interpretation is needed.

Use the lightest safe execution mode:
- parent direct execution for deterministic steps
- auxiliary worker for cheap bounded inference
- Qwen CLI worker for cheap silent external helper tasks
- delegated subagent only when a real isolated child agent is warranted

## Source of Truth

Use these in priority order:

1. CLI JSON command output
2. workspace files created by commands
3. database-backed feature state exposed by commands
4. shared library contents
5. chat/session context only as fallback operator context

## Core Features the Orchestrator Coordinates

These are the main services already present in the Python rewrite:

- `PipelineService`
- `SharePointService`
- `TaggingService`
- `TrimService`
- `HooksService`
- `VariantsService`

The orchestrator should respect those boundaries.

## When to Stay in the Parent

Use direct command execution for:

- `init workspace`
- `init db`
- `assets list`
- `ingest run`
- `trim run`
- `trim clip`
- `tag auto`
- `tag ai`
- `tag pending`
- `tag approve`
- `variants generate`
- `variants assemble`
- `variants export`
- `variants validate`
- `pipeline run`
- `sharepoint setup/list/download/upload`

These commands already have typed service boundaries and machine-readable outputs. Prefer using them directly unless interpretation or review summarization is the real problem.

## When to Delegate

Delegate only when the task needs bounded domain reasoning, such as:

- choosing the safest SharePoint search/download sequence for a messy variant query
- interpreting AI analysis results and review state for a human gate
- deciding a trim strategy from CTA boundaries or other segment signals
- summarizing validation output into a delivery-readiness handoff

## Recommended Worker Roles

- SharePoint
- Analysis
- Assembly
- QA

## Task Contract Resolution

Before executing a mix/trim/assembly request, the orchestrator must decide whether the task contract is explicit enough to act.

If key execution choices are missing, ask a minimal clarification set first instead of silently assuming defaults.

Common underspecified cases:

- "mix V204 với V212"
- "cắt CTA khỏi V204"
- "assemble/export bản này"

For ambiguous video requests, clarify only the fields that materially affect execution, such as:

- source order or lead variant
- which clip should have CTA removed
- aspect ratio
- target duration or whether the user wants a full-length vs shortened result
- output destination layer: workspace-local artifact vs reusable shared-library artifact
- whether the user wants exploratory planning only or immediate execution

If the request is already explicit enough, do not ask unnecessary questions.

## Default Flow Patterns

### 1. Local-first asset lookup

For source-media requests:

1. check workspace-local artifacts if the task is job-specific
2. check shared library if the asset is reusable or external-source oriented
3. use SharePoint only when the asset is missing locally

### 2. Review-aware pipeline progression

For full or partial pipeline requests:

1. run deterministic steps directly
2. inspect pending review state
3. if review is required, block cleanly
4. only continue after explicit approval

### 3. CTA-aware trimming flow

For requests like removing or isolating CTA:

1. resolve the source file locally or via SharePoint
2. inspect available AI analysis metadata
3. delegate Analysis if interpretation is needed
4. delegate Assembly only after trim boundaries are clear enough for action
5. verify the trimmed output path and database state

## Output Expectations

The orchestrator should preserve and summarize:

- which command actually ran
- which artifact is authoritative now
- whether a human gate still blocks progression
- what next bounded role or action is appropriate

## Anti-Drift Rules

- Do not invent a second pipeline state machine when feature services already expose the real workflow.
- Do not bypass review gates just because downstream commands exist.
- Do not send whole repo context to workers.
- Do not treat worker scratch notes as canonical truth.

## Optional Scratch State

If helpful, keep small role-local scratch files under:

```text
<workspace>/logs/agent-state/
  orchestrator.json
  analysis.json
  assembly.json
  qa.json
  sharepoint.json
```

Keep them concise and overwrite-oriented.
Do not use them as the primary workflow truth.
