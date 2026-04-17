# Worker Invocation Patterns

This document provides copy-pasteable invocation patterns for the two lightweight worker modes:
- auxiliary worker
- Qwen CLI worker

Use `execution-modes.md` first to decide whether the task should stay in the parent, use a lightweight worker, or escalate to a delegated subagent.

## 1. Auxiliary worker pattern

Use this when the parent already has all needed evidence and only needs a cheap bounded model call.

Properties:
- direct model call
- no independent tool loop
- parent executes all real commands
- best for summarization, classification, compact handoffs, and small bounded recommendations

## Parent-side pattern

1. Run the deterministic command yourself.
2. Keep only the relevant machine-readable result.
3. Build a bounded prompt.
4. Call the cheap model through the auxiliary path.
5. Parse the response.
6. Parent decides and executes the next command.

## Prompt shape

Use a prompt like this:

```text
Task: summarize one bounded workflow state for the parent orchestrator.

Question:
<EXACT_QUESTION>

Evidence:
<COMPACT_JSON_OR_BULLETS_ONLY>

Return exactly:
- Status
- Summary
- Suggested Next Action
- Reason
```

## Good auxiliary examples

### Example A: pending-review explanation

Parent flow:
1. run `tag pending --json`
2. extract only the relevant blocked/ready fields
3. call auxiliary worker
4. parent decides whether to stop for review

Example prompt:

```text
Task: summarize one bounded workflow state for the parent orchestrator.

Question:
Does this result mean the pipeline must stop for human review, or is it safe to continue?

Evidence:
{
  "pending": 2,
  "approved": 8,
  "blocked": true,
  "clips": [
    {"name": "V204", "reason": "cta confidence low"},
    {"name": "V212", "reason": "human review required"}
  ]
}

Return exactly:
- Status
- Summary
- Suggested Next Action
- Reason
```

### Example B: analysis condensation

```text
Task: summarize one bounded workflow state for the parent orchestrator.

Question:
Summarize CTA timing and confidence for trim planning.

Evidence:
{
  "cta_present": true,
  "cta_start_seconds": 8.5,
  "cta_end_seconds": 12.0,
  "confidence": "medium",
  "analysis_path": "/abs/workspace/logs/analysis/V204.json"
}

Return exactly:
- Status
- Summary
- Suggested Next Action
- Reason
```

## Important auxiliary rule

Auxiliary workers do not execute commands.
They only think, summarize, classify, or propose.
The parent remains responsible for:
- command execution
- artifact verification
- review-gate handling
- final decision making

## 2. Qwen CLI worker pattern

Use this when you want a cheap silent external worker process.

Properties:
- external CLI process
- JSON output
- good for bounded helper or small implementation tasks
- can be more autonomous than an auxiliary worker

## Recommended silent-run defaults

- fixed Qwen binary
- `--output-format json`
- `--channel CI`
- timeout wrapper
- explicit approval mode
- bounded prompt

Prefer:
- `--approval-mode plan` for helper/summarization/classification tasks
- `--approval-mode yolo` only for intentionally tool-using implementation tasks

## Minimal invocation template

```bash
QWEN=/home/brewuser/.nvm/versions/node/v20.20.0/bin/qwen
PROMPT_FILE=$(mktemp)
printf '%s' "$PROMPT" > "$PROMPT_FILE"
timeout 120 \
  OPENAI_API_KEY='your-api-key-1' \
  QWEN_CODE_DISABLE_UPDATE_NOTIFIER=1 \
  "$QWEN" "$(cat "$PROMPT_FILE")" \
  --auth-type openai \
  --openai-base-url http://127.0.0.1:8317/v1 \
  -m coder-model \
  --approval-mode plan \
  --output-format json \
  --channel CI
rm -f "$PROMPT_FILE"
```

## Helper-task example

```bash
PROMPT='Summarize this validation result in 4 bullets and end with one suggested next action.'
cat validation.json | \
  OPENAI_API_KEY='your-api-key-1' \
  QWEN_CODE_DISABLE_UPDATE_NOTIFIER=1 \
  /home/brewuser/.nvm/versions/node/v20.20.0/bin/qwen "$PROMPT" \
  --auth-type openai \
  --openai-base-url http://127.0.0.1:8317/v1 \
  -m coder-model \
  --approval-mode plan \
  --output-format json \
  --channel CI
```

## Small implementation-task example

Use only for bounded tasks such as:
- under ~50 changed lines
- touches no more than ~3 files
- parent will review after completion

```bash
PROMPT='Update the trim metadata writer to include source_path and trim_reason, touching only the smallest necessary files. Return a concise summary of edits.'
OPENAI_API_KEY='your-api-key-1' \
QWEN_CODE_DISABLE_UPDATE_NOTIFIER=1 \
timeout 120 \
  /home/brewuser/.nvm/versions/node/v20.20.0/bin/qwen "$PROMPT" \
  --auth-type openai \
  --openai-base-url http://127.0.0.1:8317/v1 \
  -m coder-model \
  --approval-mode yolo \
  --output-format json \
  --channel CI
```

## Important Qwen-worker rule

Do not use a Qwen CLI worker as a synonym for a delegated subagent.
It is still a lightweight external worker pattern unless the parent explicitly wraps it in a stronger child-agent contract.

## Escalation rule

Escalate from lightweight workers to a delegated subagent when:
- the task needs an isolated reasoning loop
- the task needs tool use beyond a bounded one-shot helper task
- the evidence is ambiguous enough that one prompt is not safe
- the parent would otherwise absorb too much context

## Quick selection checklist

Use parent direct execution when:
- the next step is deterministic

Use auxiliary worker when:
- the worker only needs to think and return a compact verdict

Use Qwen CLI worker when:
- you want a cheap silent external helper or bounded implementation worker

Use delegated subagent when:
- a real isolated child agent is actually needed
