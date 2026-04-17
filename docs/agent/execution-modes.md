# Execution Modes for Parent + Workers

This document defines the three execution modes the parent orchestrator may use in the Python rewrite of `hbs-ads`.

Use this to avoid calling everything a "subagent".

## Why this matters

Different task shapes need different levels of machinery.

If the parent treats every helper call as a full delegated subagent, orchestration becomes slower, noisier, and more expensive.
If the parent treats every ambiguous reasoning task as a cheap helper call, workflow safety and review handling become too weak.

## The three execution modes

### 1. Auxiliary worker

Use this when the parent only needs a cheap, bounded model call.

Properties:
- direct model call
- no independent tool loop
- no child session lifecycle
- parent prepares the exact prompt and inputs
- parent executes all real commands and file operations
- suitable for routing through Hermes auxiliary config or another direct model endpoint

Good fits:
- summarize command output
- condense analysis JSON into a compact handoff
- classify a bounded state into a small set of outcomes
- produce a short review summary
- convert verbose machine output into parent-usable bullets or JSON

Do not use it for:
- open-ended investigation
- ambiguous execution planning with missing evidence
- direct file edits or command execution by the worker
- any case that needs real tool use or retries inside the worker

Mental model:
- cheap brain
- parent keeps the hands

### 2. Qwen CLI worker

Use this when you want a cheap external worker process with bounded autonomy.

Properties:
- launched as a silent CLI run
- typically non-interactive with JSON output
- useful for small implementation or bounded helper tasks
- can be stricter or more autonomous depending on approval mode
- still separate from Hermes delegated-subagent semantics unless explicitly wrapped that way

Recommended invocation style for silent runs:
- fixed `qwen` binary
- `--output-format json`
- `--channel CI`
- timeout wrapper
- bounded prompt
- explicit approval mode (`plan` for helpers, `yolo` only for intentionally tool-using tasks)

Good fits:
- small coding edits
- bounded implementation tasks
- one-shot repo-aware helper tasks
- cheap classification/summarization if the CLI path is already available

Do not treat this as identical to a delegated subagent unless the parent is explicitly managing it as one.

### 3. Delegated subagent

Use this when the task truly needs an isolated child agent.

Properties:
- isolated child context
- its own agent loop
- may use tools
- bounded by explicit task contract and max iterations
- returns a structured handoff rather than raw transcript

Good fits:
- ambiguous source selection
- review-aware interpretation
- trim strategy selection from partial evidence
- delivery-readiness assessment that needs more than a cheap verdict
- any bounded task where the child needs its own reasoning loop

## Decision rule

Prefer the lightest mode that is still safe.

Use this order:
1. parent direct execution for deterministic commands
2. auxiliary worker for cheap bounded inference
3. qwen CLI worker for cheap external helper/implementation tasks
4. delegated subagent only when a real child agent is warranted

## Practical decision table

### Stay in parent

Use parent execution when:
- the CLI command is deterministic
- the next step is already obvious
- the output only needs verification, not interpretation

### Use auxiliary worker

Use an auxiliary worker when:
- the parent can collect all relevant evidence first
- the worker only needs to think, summarize, classify, or propose
- the parent will still execute the next command itself

### Use Qwen CLI worker

Use a Qwen CLI worker when:
- you want a cheap silent external worker
- the task is bounded and can fit a one-shot prompt well
- the worker may need lightweight repo-aware behavior
- a full Hermes delegated child would be overkill

### Use delegated subagent

Use a delegated subagent when:
- the task needs its own reasoning loop
- the task may need tool use
- the next step is not safely reducible to one bounded prompt
- the parent would otherwise absorb too much context

## Parent-side responsibility never changes

Regardless of worker mode, the parent still owns:
- intent resolution
- workspace vs shared-library path decisions
- review gate preservation
- final command execution for deterministic workflow steps
- artifact verification
- final decision to continue, stop, retry, or ask the user

## Vocabulary rule

Use these names consistently:
- auxiliary worker = cheap direct model call
- qwen CLI worker = cheap external silent worker process
- delegated subagent = real isolated child agent

Do not casually call all three "subagents".

## py-hbs-ads examples

### Example A: `tag pending` explanation
- parent runs `tag pending --json`
- auxiliary worker summarizes blocked vs ready state
- parent decides whether to stop for review

### Example B: small bounded coding task
- parent scopes a ≤3-file implementation task
- qwen CLI worker executes silently with JSON output
- parent reviews result and decides whether more work is needed

### Example C: ambiguous CTA trim strategy
- parent resolves local sources first
- if trim strategy is still ambiguous, spawn delegated Analysis or Assembly
- parent executes resulting deterministic trim command only after the contract is explicit
