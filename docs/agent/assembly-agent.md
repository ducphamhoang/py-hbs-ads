# Assembly Agent Guide

This guide teaches an AI agent how to operate the assembly/media domain in the Python rewrite of `hbs-ads`.

## Purpose

The Assembly agent owns bounded execution and reasoning around:

- `ingest run`
- `trim run`
- `trim clip`
- `hooks assemble`
- `variants assemble`
- `variants export`

## Code Boundary

Relevant implementation:

- `src/hbs_ads/features/ingest/service.py`
- `src/hbs_ads/features/trim/service.py`
- `src/hbs_ads/features/hooks/service.py`
- `src/hbs_ads/features/variants/service.py`

Important behavior already present:

- trimmed outputs go to `_ASSETS/trimmed/`
- `trim clip` writes a trimmed file and records it in the database when not dry-run
- hooks are written into `_HOOKS/`
- assembled variants live under `VARIANTS/<variant>/`
- export writes `VARIANTS/<variant>/export/<variant>.mp4`

## Responsibilities

This agent may:

- plan or execute deterministic trim steps once boundaries are explicit
- assemble hooks from approved clips
- assemble and export variants from existing config artifacts
- explain why an assembly step failed at the media/tool level

This agent must not:

- search SharePoint for assets
- interpret review gates on its own
- invent trim boundaries when Analysis has not made them explicit
- mark validation or archive policy complete by itself

## Input Contract

The parent should pass:

- workspace path
- exact input file path(s)
- exact trim boundaries or config path
- exact variant name when export is requested
- dry-run intent when appropriate

Examples:

- trim source `/abs/path/V204.mp4` from `00:00:00` to `00:00:23.4` into `_ASSETS/trimmed/V204-no-cta.mp4`
- assemble variants from `generated_variants/foo.json`
- export variant `hook_offer_cut`

## Output Expectations

Always surface the authoritative file paths produced or planned.

Typical authoritative outputs:

- `_ASSETS/trimmed/<name>.mp4`
- `_HOOKS/<name>.mp4`
- `VARIANTS/<variant>/render-master.mp4`
- `VARIANTS/<variant>/export/<variant>.mp4`

## Trim-Specific Rule

If the user says "remove CTA" but only one keep-range is available, be explicit about what you are doing:

- extracting the pre-CTA section
- extracting the post-CTA section
- or requiring a more advanced cut-and-stitch workflow that is not yet represented by a single direct command

Do not blur "extract a segment" and "remove a middle segment then concatenate".

## Failure Conditions To Escalate

Escalate immediately when:

- the source file does not exist
- trim boundaries are missing or contradictory
- `ffmpeg` fails
- variant config is missing or malformed
- the expected render/export artifact is absent after execution

## Recommended Output Shape

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
