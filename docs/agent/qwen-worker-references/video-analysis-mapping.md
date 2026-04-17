Video analysis mapping for py-hbs-ads orchestrator

Purpose
- Give the parent orchestrator a fast question -> evidence -> command -> next-step map for video analysis tasks.
- Use this before deciding whether to keep work in the parent, call a bounded Qwen worker, or escalate to human review.

Core rule
- Prefer existing stored analysis/metadata first.
- Re-run analysis only when required evidence is missing, stale, or too ambiguous.
- Do not auto-clear review gates unless the parent explicitly requests approval.

Question-to-analysis mapping

| Parent question | Preferred evidence source | Command / lookup path | Key fields to inspect | Good-enough signal | Next action if good | Block / escalate when |
|---|---|---|---|---|---|---|
| Does this clip have a CTA? | Stored clip analysis first, then fresh AI analysis | Existing `analysis_json` / prior handoff; else `hbs-ads --workspace <WS> tag ai` | `cta_present`, `confidence`, `notes`, `text_on_screen` | `cta_present` is explicit and confidence is not low/ambiguous | Parent can route to Assembly or continue analysis | `cta_present` missing, confidence low, or notes contradict expected structure |
| Where does the CTA start/end? | Stored Gemini/tagging analysis first | Existing `analysis_json`; else `tag ai` | `cta_start_seconds`, `cta_end_seconds`, `cta_present`, `confidence` | start/end both present and consistent with CTA present | Parent can prepare no-CTA trim plan | start/end missing, null, or confidence too weak |
| Can we trim a no-CTA version now? | CTA timing + review state | `analysis_json` + `hbs-ads --workspace <WS> tag pending` | `cta_start_seconds`, `cta_end_seconds`, `confidence`, pending clip set | CTA boundary is explicit and no unresolved review blocker for the relevant clip | Parent executes deterministic trim or delegates bounded Assembly worker | CTA timing ambiguous or clip is still pending approval |
| Is the current analysis good enough for Assembly? | Analysis handoff + stored metadata | Analysis worker output or existing analysis JSON | CTA fields, semantic cut notes, caveats, confidence | handoff clearly states exact source path and keep/remove ranges or cut-point rationale | Route to Assembly worker or parent deterministic execution | recommended action still says human review / more analysis needed |
| Is pipeline progression blocked by review? | Review state, not free-form interpretation | `hbs-ads --workspace <WS> tag pending` and prior review handoff | pending clip paths, approval requirement, clip-specific blocker notes | no pending clips for the relevant scope and no explicit approval blocker remains | Continue to generation/assembly if the parent request allows | any relevant clip still pending or approval status is unclear |
| What semantic cut points or mix handoff points look promising? | Stored Gemini notes first; fresh AI analysis only if needed | Existing `analysis_json` / prior handoff; else `tag ai` | `notes`, `text_on_screen`, CTA timing, reusable semantic notes | notes identify hook/setup/payoff or a credible handoff region with caveats | Parent can draft a bounded mix/assembly worker prompt | notes are generic, missing, or not strong enough for an editing decision |
| Is this clip likely reusable as a library artifact? | Path intent + output contract + evidence quality | Parent decision plus analysis/trim verification | workspace-vs-library intent, verification result, source provenance, confidence | intended as reusable output, verified media, provenance is clear | trim in workspace, verify, then promote to library with metadata | destination layer is ambiguous or source/provenance is unclear |
| Do we need fresh Gemini analysis, or can we reuse existing metadata? | Existing metadata first | inspect stored `analysis_json`, `gemini_tagged`, prior handoffs | `gemini_tagged`, CTA fields, semantic notes, confidence, timestamp/provenance if available | fields needed by current question already exist and are coherent | reuse metadata and avoid re-analysis | required fields absent, contradictory, or tied to the wrong source clip |
| Should we ask a human reviewer now? | Combined ambiguity / gate check | Analysis handoff + `tag pending` + parent context | confidence, contradictions, missing fields, pending review state | none; this is the stop path | stop and request human review with concise blocker handoff | whenever CTA timing, source choice, or review state cannot be made explicit safely |

Operational guidance
- Parent direct execution is best for deterministic commands once boundaries are explicit.
- Qwen worker is best for bounded interpretation/summarization with explicit inputs and output headings.
- A delegated subagent is only needed when the next step truly needs an isolated reasoning loop beyond a simple bounded worker.

Recommended evidence order
1. Existing clip analysis / prior handoff
2. `tag pending` review-state check
3. Fresh `tag ai` only if required fields are missing or stale
4. Human review if ambiguity remains

Useful command snippets
- `hbs-ads --workspace <WS> tag auto`
- `hbs-ads --workspace <WS> tag ai`
- `hbs-ads --workspace <WS> tag pending`
- `hbs-ads --workspace <WS> tag approve --all` (only with explicit parent approval)

Fields currently available from AI clip analysis
- `concept`
- `vibe`
- `style`
- `has_sfx`
- `text_on_screen`
- `notes`
- `confidence`
- `cta_present`
- `cta_text`
- `cta_start_seconds`
- `cta_end_seconds`
- `total_duration_seconds`

What we analyze well today
- CTA presence
- CTA approximate boundaries
- visible text / likely CTA text
- coarse concept / vibe / style classification
- semantic notes useful for hook/setup/payoff reasoning
- review-state support via pending/approved status

What still needs caution
- low-confidence CTA timing
- semantic handoff choices for mix/editing
- any decision that implicitly clears a review gate
- workspace-vs-library destination choices when the user has not been explicit
