# Creative Market Research Orchestration Recipes

> **Purpose:** Show how a parent AI agent should combine the market research primitives in `~/work/py-hbs-ads` into useful bounded workflows.

## 1. Framing

These are **recipes**, not rigid pipelines.

Each recipe assumes:
- the parent agent chooses the scope
- the parent agent preserves artifact paths and review state
- the parent agent can stop after any stage if the result is already sufficient

The goal is not “always run everything.”
The goal is “run the minimum useful bounded sequence.”

## 2. Recipe format

Each recipe includes:
- use case
- when to use it
- required inputs
- step sequence
- stop conditions
- review risks
- expected artifacts

---

## Recipe A — Quick manifest sanity pass

### Use case
A new market export has arrived and the parent agent wants to know whether it is structurally usable before doing any expensive analysis.

### When to use
- right after browser/export collection
- before clustering or Gemini analysis
- when the sample may be messy or underspecified

### Required inputs
- research brief
- raw manifest path
- run id or provisional run id

### Steps
1. validate brief
2. normalize candidates from raw manifest
3. validate a sample of normalized candidates
4. compute quick enrichment summaries:
   - source distribution
   - platform distribution
   - geo distribution
   - app/publisher distribution
5. optionally persist normalized output

### Stop conditions
Stop here if:
- the manifest is malformed
- the brief is too weak
- the sample is clearly too small or too biased
- the operator only asked for intake QA

### Review risks
- hidden source bias
- missing source identifiers
- market scope mismatch between brief and manifest

### Expected artifacts
- `collect/candidates.raw.json`
- `normalize/candidates.normalized.json`
- `enrich/context.json`

---

## Recipe B — Cluster a collected sample before any AI analysis

### Use case
The parent agent wants to reduce duplicate noise and choose representative assets before paying for model analysis.

### When to use
- after normalization
- before Gemini
- when many ads are likely just slight variants or reuploads

### Required inputs
- normalized candidates

### Steps
1. run clustering
2. inspect:
   - asset count vs candidate count
   - variant cluster count
   - concept cluster count
   - low-confidence cluster metrics
3. choose representative assets from variant clusters
4. decide whether concept grouping is good enough for downstream use

### Stop conditions
Stop here if:
- clustering is the actual task
- concept groups need human review first
- there are too few useful representatives to justify Gemini analysis

### Review risks
- over-merging concept clusters
- under-merging duplicate uploads

### Expected artifacts
- `cluster/asset-dedupe.json`
- `cluster/variant-clusters.json`
- `cluster/concept-clusters.json`

---

## Recipe C — Analyze a few representative creatives deeply

### Use case
The parent agent only needs insight from a small, representative set rather than a full sample.

### When to use
- exploration
- debugging taxonomy/prompt quality
- reviewing one competitor or one concept family

### Required inputs
- representative asset paths
- run id
- optional analysis focus

### Steps
1. call `analyze_asset(...)` per selected asset
2. validate each analysis payload
3. inspect `quality` and `evidence`
4. reject invalid or weak outputs
5. persist or save successful analyses

### Stop conditions
Stop here if:
- the task was only to analyze a few creatives
- the model output quality is not yet trustworthy enough for synthesis
- the taxonomy still needs iteration

### Review risks
- overinterpreting one asset as market truth
- accepting schema-valid but semantically weak evidence

### Expected artifacts
- `analyze/creative-analysis.jsonl`
- `analyze/failures.json`

---

## Recipe D — Draft first-pass insight cards from existing analyses

### Use case
The team already has validated analyses and wants draft insights quickly.

### When to use
- after analyzing a bounded sample
- when the goal is reviewable drafts, not final truth

### Required inputs
- research brief
- validated analyses
- current run id
- optional cluster context

### Steps
1. filter analyses to `analysis_status == ok`
2. synthesize insight candidates
3. validate each insight candidate
4. sort by confidence / supporting count
5. stop with draft outputs ready for review

### Stop conditions
Stop here if:
- reviewed publication is not needed yet
- the operator only wants candidate insights

### Review risks
- insight inflation from small samples
- assuming pattern density implies market-wide trend

### Expected artifacts
- `synthesize/insight-candidates.json`

---

## Recipe E — Re-synthesize after changing the brief

### Use case
The underlying analyses are still useful, but the question changed.

### When to use
- same sample, different lens
- same analyses, new strategic question
- same dataset, different scope framing

### Required inputs
- old analyses
- new or revised brief
- run id for the new synthesis pass

### Steps
1. validate the revised brief
2. reuse prior validated analyses
3. rerun synthesis with the new brief
4. compare new insight set with the prior one
5. persist as a distinct synthesis pass if needed

### Stop conditions
Stop here if:
- the new brief reveals the old sample is invalid for the new question
- new analysis dimensions are required and current analyses are too shallow

### Review risks
- false confidence because reused analyses feel “already approved”
- scope mismatch between old sample and new question

### Expected artifacts
- updated `synthesize/insight-candidates.json`
- optional comparison note or delta artifact

---

## Recipe F — Human review gate on insight drafts

### Use case
Draft insights exist and the parent agent wants a structured approval step.

### When to use
- before canonizing claims
- before experiment recommendations are treated as guidance
- before sync into more durable knowledge surfaces

### Required inputs
- draft insight candidates
- reviewer identity
- decision(s)

### Steps
1. validate each candidate
2. apply review decisions:
   - approve
   - approve_with_edits
   - reject
   - defer_for_more_evidence
3. persist review records
4. separate approved vs rejected vs deferred outputs

### Stop conditions
Stop here if:
- the user wants review output only
- no durable sync is required yet

### Review risks
- approving evidence-light claims under time pressure
- collapsing “interesting idea” into “approved insight”

### Expected artifacts
- `review/review-decisions.json`

---

## Recipe G — Persist bounded results to research DB

### Use case
The parent agent has enough bounded outputs and wants durable local state.

### When to use
- after any meaningful stage
- especially after reviewable milestones
- when later reuse matters

### Required inputs
- brief
- candidates
- clusters
- analyses
- insights
- reviews
- sync report data

### Steps
1. bootstrap research DB if needed
2. upsert brief
3. upsert candidates
4. upsert clusters
5. upsert analyses
6. upsert insights
7. upsert reviews
8. write sync report

### Stop conditions
Stop here if:
- persistence is the only missing step
- no further reasoning is required now

### Review risks
- storing weak drafts without clear status labels
- mixing pilot research state into unrelated operational DBs

### Expected artifacts
- `sync/sync-report.json`
- `research.db`

---

## Recipe H — Minimal useful end-to-end bounded run

### Use case
The parent agent wants one practical end-to-end pass, but still wants boundedness and observability.

### When to use
- smoke tests
- local pilot runs
- one brief + one manifest + one sample window

### Required inputs
- brief
- manifest path
- workspace path

### Steps
1. validate brief
2. normalize manifest
3. cluster
4. analyze representative assets only
5. synthesize draft insights
6. optional review transform
7. sync bounded results

### Important rule
This recipe is still **tool-first composition**.
It should remain easy to stop between steps.

### Stop conditions
Stop early if:
- no valid representatives exist
- analysis quality is weak
- insight synthesis yields only noise

### Review risks
- treating the recipe as a mandatory one-size-fits-all pipeline

---

## 3. Recommended defaults for parent agents

## Default 1 — Prefer the shortest recipe that answers the question
Do not run full end-to-end composition unless the user actually needs it.

## Default 2 — Use Recipe C and D often
In practice, “analyze a few representative creatives” + “draft first-pass insights” will probably be the highest-value pair.

## Default 3 — Separate draft from approved outputs
Insight generation and insight approval are different steps.

## Default 4 — Preserve artifacts and paths
Every recipe should leave behind enough artifacts for rerun, review, or synthesis reuse.

## Default 5 — Treat the runner as convenience, not architecture
The runner is useful, but the core value is still the primitive toolset.

## 4. What should come next after these recipes

The next useful doc after this one would be one of:
- a **representative asset selection policy**
- a **review policy for insight approval thresholds**
- a **browser-collection handoff contract** for authenticated market tools

Those three docs would make the tool-first system much more operationally stable.
