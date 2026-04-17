# Multi-Agent Pipeline Guides

This folder defines the recommended agent split for the Python rewrite of `hbs-ads`.

These guides are implementation-facing instructions for AI agents or subagents that operate on a workspace. They are not the canonical architecture docs; they are the practical role contracts for delegated work.

## Current Agent Set

- `orchestrator-agent.md`
- `sharepoint-agent.md`
- `analysis-agent.md`
- `assembly-agent.md`
- `qa-agent.md`
- `delegation-contracts.md`
- `workflow-examples.md`
- `execution-modes.md`
- `worker-invocation-patterns.md`
- `notion-media-scrum-policy.md`
- `notion-media-scrum-routine.md`
- `reusable-library-trim-workflow.md`
- `prompts/sharepoint-worker-template.md`
- `prompts/analysis-worker-template.md`
- `prompts/assembly-worker-template.md`
- `prompts/qa-worker-template.md`

## Why this split

The Python rewrite already has clear feature boundaries in code:

- `PipelineService` coordinates top-level flow
- `SharePointService` handles setup/upload/download/list
- `TaggingService` handles heuristic tagging, AI analysis, approval, and review lookup
- `TrimService`, `HooksService`, and `VariantsService` own media assembly work
- `VariantsService.validate()` owns validation output for delivery readiness

The agent split should follow those boundaries instead of inventing a second architecture.

## Parent/Worker Model

Use one parent orchestrator plus bounded workers.

- The parent orchestrator resolves intent, paths, and stage order.
- Workers handle one bounded domain task.
- Workers may recommend a next role, but they do not self-dispatch other workers.
- Canonical workflow truth lives in workspace artifacts and command results, not in chat memory.
- Not every worker is a delegated subagent; see `execution-modes.md` for the distinction between auxiliary workers, Qwen CLI workers, and delegated subagents.

## Default Path Model

Local defaults for this environment:

```text
repo root:            ~/work/py-hbs-ads
workspace root:       <job-specific path passed to --workspace>
shared library root:  ~/work/video-library
```

Workspace is for ephemeral job state.
Shared source media and reusable outputs belong in the shared library when appropriate.

## JSON-First Rule

When the CLI supports JSON output, prefer it for automation-safe orchestration.

At minimum, parent/orchestrator logic should preserve:

- command name
- status
- message
- dry_run
- machine-readable `data`

## Review Gate Rule

The Python pipeline explicitly blocks at review when clips are still pending approval.

That means:

- Orchestrator must preserve review gates.
- Analysis may summarize pending state.
- Only explicit approval clears the gate.
- Downstream generation/assembly/export should not pretend review already happened.

## Output Contract for Workers

Each worker should return a concise handoff with these headings:

- Stage
- Status
- Authoritative Artifacts
- Requires Human Review
- Review Gate
- Allowed Next Stages
- Blocking Issues
- Summary
- Suggested Next Role
- Suggested Next Action
- Reason
- Context For Parent

The last four fields are optional recommendations, not self-dispatch authority.

## Suggested Chain Policy

- Keep delegated reasoning chains shallow; default maximum depth is 3 worker steps.
- Do not re-invoke the same role in one chain unless it is an explicit retry with new evidence.
- If a task is mechanical and deterministic, parent should usually execute it directly instead of delegating.
- If a further delegation would exceed the chain budget, parent should stop and summarize the deferred next step.

## Relationship to Existing Docs

Read these first for canonical context:

- `../architecture.md`
- `../operator_guide.md`
- `../parity_matrix.md`

Then use the agent guides in this folder for role-specific execution behavior.

Suggested reading order:

1. `README.md`
2. `orchestrator-agent.md`
3. `delegation-contracts.md`
4. `execution-modes.md`
5. `worker-invocation-patterns.md`
6. `notion-media-scrum-policy.md` and `notion-media-scrum-routine.md` when the task is team coordination through Notion
7. one role guide as needed
8. one prompt template for the role you are about to spawn
9. `workflow-examples.md` for concrete parent/subagent patterns
10. `reusable-library-trim-workflow.md` for requests that should end as canonical reusable library artifacts
