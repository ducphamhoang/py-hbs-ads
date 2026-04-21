# Creative Market Research Workflow Docs

This folder is the implementation-planning layer for a new **creative market research** workflow in `py-hbs-ads`.

It is intentionally separate from the existing canonical rewrite docs:

- `../README.md` explains the current parent/worker orchestration model.
- `../../architecture.md` is the current codebase architecture truth for the Python rewrite.
- This folder defines the **next workflow family** we want to add: market collection -> creative analysis -> evidence-backed insight synthesis.

## Documents

- `creative-market-research-prd-2026-04-20.md`
- `creative-market-research-v1-agent-definition-of-done.md`
- `creative-market-research-architecture-plan-2026-04-20.md`
- `creative-market-research-workflow-spec.md`
- `creative-market-research-data-model.md`
- `gemini-creative-analysis-schema.md`
- `creative-market-research-tool-catalog.md`
- `creative-market-research-agent-usage-contracts.md`
- `creative-market-research-orchestration-recipes.md`
- `creative-market-research-browser-collection-handoff-contract.md`

## Scope

These docs cover a workflow where Hermes can:

1. collect ad candidates from authenticated market-intelligence tools via browser-driven operator flows
2. normalize and deduplicate the candidate set
3. analyze representative creative videos with Gemini using a strict JSON contract
4. enrich the results with market and competitor context
5. synthesize evidence-backed insights
6. sync both evidence and synthesis into reusable research storage

## Current implementation emphasis

The current preferred implementation framing is **tool-first**:

- build agent-usable primitives first
- use those primitives in parent orchestration
- treat end-to-end pipeline composition as a later layer

So for the near term, the most important docs after the PRD/architecture set are:
- `creative-market-research-tool-catalog.md`
- `creative-market-research-agent-usage-contracts.md`
- `creative-market-research-orchestration-recipes.md`
- `creative-market-research-browser-collection-handoff-contract.md`

## Layering rule

These docs are a planning and orchestration layer, not yet the canonical implementation truth of the existing codebase.

Precedence for implementation decisions:

1. `../../architecture.md`
2. `../../operator_guide.md`
3. `../README.md` and existing role docs under `../`
4. the docs in this folder

If implementation later differs from this plan, the implementation and canonical architecture docs win.
