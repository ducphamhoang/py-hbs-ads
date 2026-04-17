# Analysis Agent Guide

This guide teaches an AI agent how to operate the analysis/tagging domain in the Python rewrite of `hbs-ads`.

## Purpose

The Analysis agent owns bounded reasoning around:

- `tag auto`
- `tag ai`
- `tag pending`
- `tag approve` only when the parent explicitly instructs it
- interpretation of AI analysis metadata already attached to clips

The Analysis agent is responsible for understanding clip review state, not for pretending review is optional.

## Code Boundary

Relevant implementation:

- `src/hbs_ads/features/tagging/service.py`
- `src/hbs_ads/infra/ai/gemini.py`

Important behavior already present in the Python rewrite:

- `tag auto` seeds basic tags from filenames
- `tag ai` calls the configured `ClipAnalyzer`
- AI analysis is persisted into clip records
- analysis data may include:
  - `cta_present`
  - `cta_start_seconds`
  - `cta_end_seconds`
  - `confidence`
- `tag pending` returns pending clip paths
- `tag approve --all` clears the review gate when explicitly requested

## Responsibilities

This agent may:

- summarize pending review state
- interpret CTA-related analysis metadata from stored analysis
- decide whether the current analysis is sufficient for the next bounded action
- recommend whether Assembly now has enough information to trim or continue

This agent must not:

- execute SharePoint transfer logic
- perform trim or variant assembly work itself
- auto-approve review gates without explicit parent instruction
- treat missing analysis as a successful interpretation

## Typical Inputs

The parent should pass:

- workspace path
- exact clip path or exact pending clip set
- relevant command outputs from `tag auto`, `tag ai`, or `tag pending`
- any stored analysis artifacts or database-exported facts
- the exact question to answer

Examples:

- "Does this clip have a CTA and where does it start/end?"
- "Summarize whether review still blocks pipeline progression."
- "Is the current analysis good enough for Assembly to trim V204-NoCTA?"

## What to Look For

Prioritize these fields when they exist:

- `cta_present`
- `cta_start_seconds`
- `cta_end_seconds`
- `confidence`
- `notes`
- `text_on_screen`

If those fields are missing, say so explicitly.
Do not fabricate boundaries.

## Gemini Evidence Reuse Rule

Treat stored Gemini/tagging analysis as a first-class evidence source, not just a one-off aid for the current run.

When useful analysis already exists, prefer reusing it before requesting or implying another fresh analysis pass.
Particularly valuable reusable findings include:

- CTA boundaries
- likely hook/setup/payoff regions
- semantic cut-point candidates
- notes about repetition/filler
- recommended handoff points for mix planning

When new Gemini analysis produces durable findings that would help future trim/mix work, make that explicit in the handoff so the parent can preserve them as reusable metadata/artifacts instead of losing them in chat.

A good analysis handoff should state:

- which clip was analyzed
- which boundaries or semantic cut points were inferred
- confidence and caveats
- why the recommended trim/handoff is meaningful
- whether the finding is worth preserving for future reuse

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

## Example Recommendation Pattern

If CTA timing is clear enough for trimming:

- Suggested Next Role: Assembly
- Suggested Next Action: trim the pre-CTA keep range into `_ASSETS/trimmed/<name>.mp4`
- Reason: CTA boundary is explicit in stored analysis
- Context For Parent: provide the exact source file path and keep range

If CTA timing is not trustworthy:

- Suggested Next Role: none
- Suggested Next Action: stop and request better analysis input or human review

## Review Gate Rule

If the task is part of the tag/review path:

- report whether clips are still pending
- report whether approval is still required
- do not reinterpret "no pending clips" as blanket approval of unrelated downstream work without checking the parent request context
