# Reusable Library Trim Workflow

This workflow standardizes requests like:

- "cắt CTA khỏi video V204 và bỏ vào library"
- "tạo reusable no-CTA asset cho V212"
- "cắt reusable pre-hook clip cho một variant"

The goal is to convert one source variant into a **canonical reusable artifact in the shared library**, while keeping parent context compact and preserving clear authority boundaries.

## Purpose

Use this workflow when the requested output is **not just a job-local workspace artifact**, but a reusable media asset that future jobs should discover under `~/work/video-library`.

## Core Rule: Separate Workspace vs Library

- **Workspace** (`--workspace PATH`) is for ephemeral job execution state.
- **Shared library** (`~/work/video-library` by default) is for persistent reusable media.
- Parent must decide which layer is canonical **before** trimming.
- Do not default to `_ASSETS/trimmed/...` as the final answer when the user explicitly wants reusable output.

## Recommended Parent + Worker Split

### Parent orchestrator owns

- intent resolution
- deciding whether the target is workspace-local or library-canonical
- final trim execution when the step is deterministic
- promotion/copy into library
- final verification
- metadata/index persistence

### Spawn workers when ambiguity exists

#### Source Resolver worker
Spawn when any of these are true:

- multiple likely source files exist
- naming is inconsistent (`V204`, `MixV204`, `V204-NewEF02`, etc.)
- one candidate may be corrupt or incomplete
- SharePoint or library lookup may require bounded exploration

Expected output:

- authoritative source candidate(s)
- rejected candidates and reasons
- whether SharePoint is still needed
- recommended next role

#### Analysis worker
Spawn when any of these are true:

- CTA boundary is not already explicit
- the trim strategy is ambiguous
- the user says "remove CTA" but the actual operation is unclear

Expected output:

- CTA presence / boundary confidence
- safe trim strategy (`pre-CTA`, `post-CTA`, or `cut-and-stitch required`)
- blocking issues if the evidence is insufficient
- recommended next role

## Standard Workflow

### 1. Resolve the task contract

Parent should make these fields explicit:

- variant id
- requested transformation
- target aspect(s)
- final target layer: `workspace` or `library`
- expected canonical output naming

Example:

```text
variant: v204
transformation: remove CTA
strategy: pre-CTA keep range
target aspects: 1080x1920, 1080x1350, 1080x1080, 1920x1080
final target: library
```

### 2. Resolve source candidates local-first

Search in this order:

1. existing canonical library artifacts if they already satisfy the request
2. shared raw source media in `~/work/video-library/raw/`
3. workspace-local artifacts if the task is explicitly job-specific
4. other known local source repositories if the library does not yet contain the needed source
5. external source locations or SharePoint only if missing locally

Important distinction:

- `~/work/video-library/...` is the preferred **canonical reusable layer**
- another local repo or media workspace (for example `/mnt/d/work/...`) may still be the best **upstream source location** when the library has not been populated yet
- when that happens, parent should say so explicitly: library-first lookup failed, so the workflow is falling back to another trusted local source before trying SharePoint

If candidate selection is ambiguous, spawn **Source Resolver**.

### 3. Resolve trim boundary / strategy

If existing evidence is enough, parent may decide directly.

Otherwise spawn **Analysis** with the exact question, for example:

- "Is CTA timing explicit enough to create a reusable no-CTA library asset for V204?"
- "Should this request be interpreted as pre-CTA extraction, post-CTA extraction, or cut-and-stitch?"

### 4. Run deterministic trim

Once the source path and trim boundary are explicit, parent may execute the trim directly.

Workspace-local command outputs can still land in:

- `_ASSETS/trimmed/...`

But if the user requested a reusable asset, parent must then promote/copy the canonical result into the library, for example:

- `~/work/video-library/trimmed/v204/V204-NoCTA_1080x1920_52s.mp4`

### 5. Persist metadata next to the canonical asset

For each canonical library artifact, write a metadata JSON with fields like:

- variant
- artifact path
- source path
- workspace artifact path
- trim strategy
- start / end
- source duration
- output duration
- reasoning
- created_at
- sha256

### 6. Maintain an index for the library folder

When a variant has multiple reusable outputs, maintain an `index.json` under the library folder.

Example path:

- `~/work/video-library/trimmed/v204/index.json`

Recommended fields:

- variant
- kind
- updated_at
- artifact_count
- artifacts[] with:
  - aspect
  - duration_seconds
  - path
  - source
  - strategy
  - created_at
  - sha256
  - notes
  - metadata_path
  - workspace_artifact

This index is the machine-readable registry that future orchestrators should consult first.

### 7. Verify the canonical result

Parent should verify at minimum:

- the canonical library file exists
- the metadata file exists
- the index entry exists or is updated
- `ffprobe` returns expected duration
- checksum is recorded
- if the source had known issues, the notes explain the fallback source choice

## Naming Guidance

Prefer canonical names that make these facts obvious:

- variant id
- transformation intent
- aspect ratio
- effective duration

Example:

- `V204-NoCTA_1080x1920_52s.mp4`

## Failure Handling

Stop and summarize cleanly when:

- no trustworthy source exists
- CTA boundary is ambiguous
- the requested operation is actually cut-and-stitch, not simple extraction
- the chosen source is corrupt
- trim output duration is obviously wrong
- library promotion failed

## Example: V204 No-CTA Reusable Artifact

A successful pattern for V204 looked like this:

- user intent: remove CTA and store result in library
- source resolution: avoid corrupted standalone source, prefer intact aspect-matched mix source
- trim strategy: `pre-CTA keep range`
- canonical outputs: `~/work/video-library/trimmed/v204/V204-NoCTA_<aspect>_52s.mp4`
- registry: `~/work/video-library/trimmed/v204/index.json`

## Parent Prompt Skeleton

```text
Mission: create or update canonical reusable trim artifacts in the shared library.
Variant: <VARIANT>
Requested transformation: <REMOVE_CTA|PREHOOK|OTHER>
Target aspects: <ASPECTS>
Canonical target layer: library
Canonical library folder: <ABS_LIBRARY_FOLDER>
Known evidence:
- <CONFIGS / EXISTING REFERENCES / SOURCE PATHS>
Must enforce:
- workspace is ephemeral
- library is canonical for reusable outputs
- spawn a worker if source selection or trim strategy is ambiguous
Return:
- source chosen
- strategy chosen
- canonical artifact paths
- metadata/index paths
- verification summary
```
