# Delegation Contracts for Subagents

This document defines how the parent orchestrator should spawn bounded subagents in the Python rewrite of `hbs-ads`.

## Purpose

Use these contracts to keep parent context compact.

The goal is:

- parent resolves intent, paths, and command sequence
- parent executes deterministic CLI steps directly
- subagents handle bounded interpretation or domain reasoning
- subagents return compact handoffs instead of raw transcripts

## When to Spawn a Delegated Subagent

Spawn a delegated subagent only when at least one of these is true:

- the next step depends on domain interpretation, not just command execution
- a human review summary is needed and a cheap auxiliary worker is not enough
- a command returned machine-readable output but the safest next step is still ambiguous
- the child likely needs its own bounded reasoning loop or tool use
- the parent would otherwise need to absorb too much raw context

Do not spawn a delegated subagent for:
- simple command execution that the parent can perform directly
- cheap bounded summarization/classification that fits an auxiliary worker
- small external helper tasks that fit a silent Qwen CLI worker

See `execution-modes.md` for the taxonomy.

## Recommended Roles

- SharePoint
- Analysis
- Assembly
- QA

## Standard Parent Input Envelope

The parent should pass input in this logical shape:

```json
{
  "role": "analysis",
  "workspace": "/abs/path/to/workspace",
  "stage": "review",
  "request_goal": "determine whether CTA timing is explicit enough for trim",
  "artifacts": {
    "authoritative_inputs": [
      "/abs/path/to/source.mp4",
      "/abs/path/to/analysis.json"
    ],
    "authoritative_outputs": []
  },
  "command_results": [
    {
      "command": "hbs-ads --workspace ... tag ai --json",
      "status": "ok",
      "data": {
        "updated": 1,
        "analyses": [
          {
            "path": "...",
            "cta_present": true,
            "cta_start_seconds": 8.5,
            "cta_end_seconds": 12.0,
            "confidence": "medium"
          }
        ]
      }
    }
  ],
  "must_not_do": [
    "do not self-dispatch another role",
    "do not bypass review gates"
  ]
}
```

## Standard Worker Output Contract

Each subagent should return these headings:

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

## Suggested-Next-Role Rule

Workers may recommend a next role.
Workers may not self-dispatch a next role.
The parent orchestrator decides whether to:

- chain the suggested role now
- stop for review
- retry the current role with better inputs
- defer the next step

## Chain Policy

Default policy:

- max delegated depth: 3 worker steps
- do not re-invoke the same role in one chain unless new evidence exists
- if the next suggestion is mechanical, parent should usually do it directly
- if another delegation would exceed the budget, stop and summarize the deferred step

## Anti-Pollution Rules

- pass only the role-relevant docs and artifacts
- do not paste full raw logs unless absolutely necessary
- do not pass unrelated role docs
- keep worker outputs concise and machine-usable
- persist workflow truth in command results and workspace artifacts, not in chat memory

## Optional Scratch State

If needed, keep small role-local scratch files under:

```text
<workspace>/logs/agent-state/
  analysis.json
  assembly.json
  qa.json
  sharepoint.json
```

Suggested contents:

- latest verified artifact path
- latest interpreted boundary
- unresolved blocking question
- retry-relevant facts only

These files are not canonical workflow truth.
