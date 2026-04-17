# Workflow Examples for Parent + Subagents

This document shows how the parent orchestrator should use workers in representative Python-rewrite workflows.
Use `execution-modes.md` first so you do not overuse the word "subagent" for auxiliary or Qwen CLI helper calls.

## Example 1: Cut CTA of V204

User request:

- "cắt CTA của video V204"

### Parent steps

1. Check local-first:
   - shared library raw/trimmed
   - workspace-local assets if the request is job-specific
2. If missing locally, use SharePoint list/download.
3. Inspect available AI analysis metadata.
4. If CTA timing is already explicit, parent may call Assembly directly.
5. If CTA timing needs interpretation, spawn Analysis.
6. After Analysis returns a clear keep range, parent either:
   - executes `trim clip` directly, or
   - spawns Assembly if trim planning needs bounded reasoning.
7. Verify `_ASSETS/trimmed/<name>.mp4` exists and summarize the result.

### Suggested spawn points

Spawn SharePoint when:

- the source file is missing locally
- multiple V-range search attempts may be needed

Spawn Analysis when:

- AI analysis exists but needs interpretation
- CTA timing is present but confidence or trim strategy is unclear

Spawn Assembly when:

- the keep-range is explicit but the trim/assembly plan still needs bounded reasoning

Do not spawn QA for this workflow unless the trimmed result is intended to feed a delivery-ready variant workflow.

## Example 2: Tag -> Review -> Generate

### Parent steps

1. Run `tag auto`
2. Run `tag ai`
3. Run `tag pending`
4. If pending review exists, block cleanly
5. Spawn Analysis only to summarize review state for the user
6. Only after explicit approval, continue to variants generation

### Suggested spawn points

Spawn Analysis when:

- pending review output needs concise human-facing interpretation
- CTA or clip-analysis metadata needs bounded explanation

Do not spawn Assembly until generation or trim work is actually authorized.

## Example 3: Validate Then Upload

### Parent steps

1. Run `variants validate`
2. Inspect validation artifacts
3. Spawn QA if a concise delivery-readiness verdict is needed
4. If QA says local evidence is sufficient, parent may call SharePoint upload directly or delegate SharePoint planning/upload

### Suggested spawn points

Spawn QA when:

- validation artifacts exist but readiness still needs interpretation

Spawn SharePoint when:

- upload planning, variant naming, or target lookup is the next bounded task

## Example Parent Prompt Skeleton

```text
Mission: handle one bounded domain task and return a concise machine-usable handoff.
Role: <SharePoint|Analysis|Assembly|QA>
Workspace: <ABS_WORKSPACE_PATH>
Stage: <STAGE>
Question: <EXACT_QUESTION>
Artifacts:
- <PATHS>
Relevant command results:
- <JSON-FRIENDLY SUMMARY>
Must not do:
- do not self-dispatch another role
- do not bypass review gates
Return headings:
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
```

## Example 4: Create Reusable No-CTA Library Artifacts for V204

User request:

- "cắt CTA của V204 và bỏ vào library để tái sử dụng"

### Parent steps

1. Make the target explicit:
   - this is a **library-canonical** request, not just a workspace-local trim
   - expected canonical folder: `~/work/video-library/trimmed/v204/`
2. Check local-first in this order:
   - existing canonical library artifacts under `~/work/video-library/trimmed/v204/`
   - reusable raw media in `~/work/video-library/raw/`
   - workspace-local assets only if the task is job-specific
3. If source selection is ambiguous, spawn a bounded worker to choose the safest local source.
4. If CTA timing or trim strategy is ambiguous, spawn Analysis.
5. Once source path and keep range are explicit, parent executes the deterministic trim.
6. Promote/copy the canonical result into the shared library.
7. Write per-artifact metadata JSON and maintain `index.json` under the library folder.
8. Verify:
   - canonical file exists
   - metadata exists
   - `index.json` is updated
   - duration and checksum are recorded

### Suggested spawn points

Spawn Source Resolver when:

- multiple likely local candidates exist
- naming is inconsistent (`V204`, `MixV204`, `V204-NewEF02`)
- one candidate may be corrupt or incomplete
- SharePoint lookup might otherwise flood parent context

Spawn Analysis when:

- CTA boundary is not already explicit
- the request "remove CTA" could mean more than one trim strategy

Do not stop at `_ASSETS/trimmed/...` for this workflow when the user explicitly requested reusable output in the shared library.

## Key Principle

Spawn subagents to narrow context, not to avoid responsibility.

The parent still owns:

- command execution for deterministic steps
- artifact verification
- review-gate preservation
- final decision about whether to continue, stop, retry, or ask the user
