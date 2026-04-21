# PRD — Creative Market Research Workflow for Mobile Game Ads

> **Goal:** Build a reviewable, evidence-backed workflow that turns raw market ad signals into structured creative research, reusable insight records, and actionable experiment recommendations for mobile game ads.

## 1. Problem statement

The team already has several disconnected capabilities:

- authenticated browser-based tools for market collection
- Gemini-based video analysis that can return JSON
- local research storage and workflow orchestration surfaces in `py-hbs-ads`
- humans who can review and judge strategic relevance

What is missing is a coherent workflow contract.

Current risks if we operate ad hoc:

- market samples are pulled without durable provenance
- duplicate ads and variant spam distort pattern counts
- model-generated tags drift because taxonomy is underspecified
- insights are written as free-form notes with weak evidence links
- the resulting research store is difficult to audit, compare, or reuse

If we do not define the workflow first, we will end up with a nice-looking analysis layer that is not trustworthy enough for strategy decisions.

## 2. Product objective

Create a **Creative Market Research Pipeline** that can consistently convert ad-market observations into structured research outputs.

The workflow must:

1. accept an explicit research brief
2. collect market ad candidates from authenticated sources
3. preserve source, query, and retrieval provenance
4. normalize and deduplicate candidate ads into reusable clusters
5. analyze representative videos with a strict JSON schema
6. separate observable evidence from higher-order interpretation
7. synthesize evidence-backed insights with confidence and scope
8. support human review gates before strategic conclusions become canonical
9. sync raw evidence and curated synthesis into durable research storage

## 3. Primary users

### 3.1 Creative strategist
Needs to understand current market patterns, saturated hooks, underused concepts, and experiment opportunities.

### 3.2 Creative lead / producer
Needs concrete examples, comparable references, and cluster-level summaries rather than raw ad dumps.

### 3.3 Performance / growth collaborator
Needs structured competitive context, distribution by source/geo/platform, and frequency signals.

### 3.4 Hermes operator
Needs an explicit workflow with bounded stages, durable state, and clear review gates.

## 4. Non-goals

V1 should **not** try to:

- infer true ad performance or profitability from creative content alone
- auto-decide final creative strategy without human review
- perfectly deduplicate all variants with zero human correction
- produce broad market truth from tiny or biased samples
- redesign the full existing `py-hbs-ads` CLI in one pass
- hide uncertainty to make the system look smarter

## 5. Key product decisions

### Decision A — The workflow starts from a research brief, not a loose prompt
This prevents sampling drift and forces the run to declare scope, objective, and output mode.

### Decision B — Insight records must trace back to evidence
An insight without source ads, clusters, or supporting observations is not trustworthy enough to store as truth.

### Decision C — Variant and concept clustering are first-class, not cleanup details
Without clustering, teams that spam many edits of one concept will distort the market picture.

### Decision D — AI may draft and score insight candidates, but humans own canonization
AI can summarize, classify, and propose. Humans approve strategic truth when confidence or scope is non-trivial.

### Decision E — Separate evidence storage from synthesis storage
Raw observations and curated insight cards serve different purposes and must not be collapsed into one flat table.

## 6. User stories

### 6.1 Briefed market scan
As a strategist, I want to define a market-research brief so the workflow knows exactly what sample to collect and what question to answer.

### 6.2 Authenticated collection
As an operator, I want Hermes to use browser-authenticated tools to collect ad candidates without manually re-entering every field outside the workflow.

### 6.3 Controlled analysis
As the system, I want Gemini to return structured creative analysis with evidence references and confidence markers so downstream logic can stay deterministic.

### 6.4 Pattern synthesis
As a strategist, I want grouped, evidence-backed patterns rather than a pile of individual ad summaries.

### 6.5 Safe insight review
As a human reviewer, I want to approve, edit, reject, or defer insights before they become durable research artifacts.

### 6.6 Reusable research memory
As the team, we want to query prior findings by competitor, hook type, format, angle, or trend window without rereading every raw video.

## 7. Constraints

### 7.1 Source constraint
Many market-intelligence tools require authentication and browser interaction.

Implication:
- collection must be treated as an operator/browser-assisted stage
- collected records must preserve source and query context

### 7.2 Evidence constraint
Video analysis can be rich but imperfect.

Implication:
- schema must separate observation from interpretation
- confidence and review flags are mandatory

### 7.3 Taxonomy constraint
Free-form tags decay quickly.

Implication:
- controlled vocabularies are required for major tag families
- unknown values must be represented explicitly instead of improvising taxonomy on the fly

### 7.4 Review constraint
Strategic claims are higher risk than raw extraction.

Implication:
- market-wide claims and action recommendations need review gates

## 8. Success metrics

### 8.1 Workflow quality
- a run can be reproduced from the stored brief and query context
- every insight can point to supporting evidence records
- duplicate variant spam is reduced to stable cluster-level counts

### 8.2 Operator trust
- reviewers can see why an insight was produced
- confidence and caveats are explicit
- ambiguous cases are deferred instead of silently normalized away

### 8.3 Business usefulness
- outputs are good enough to seed creative briefs, test ideas, and competitor snapshots
- the research store becomes queryable by concept, hook, format, competitor, geo, and date window

## 9. Functional requirements

### FR1 — Research brief intake
The system must accept a structured brief with at least:
- research goal
- market scope
- competitor scope
- creative scope
- analysis focus
- sampling strategy
- output mode
- review mode

### FR2 — Candidate collection
The system must persist:
- source system
- query/filter context
- retrieved timestamp
- source-native ids/urls when available
- downloaded asset references when available

### FR3 — Normalization and deduplication
The system must support at least:
- normalized candidate records
- exact or near-exact asset-level dedupe
- variant clustering
- concept clustering with confidence

### FR4 — Creative analysis
The system must analyze representative assets and store:
- observable facts
- controlled taxonomy tags
- interpretation hypotheses
- evidence/timestamp references
- confidence and review metadata

### FR5 — Enrichment
The system must support enrichment from surrounding market context such as:
- app/store metadata
- publisher/competitor attribution
- region/platform/source distribution
- repeat frequency or historical presence when available

### FR6 — Insight synthesis
The system must produce structured insight candidates with:
- signal statement
- supporting evidence summary
- scope declaration
- confidence
- implication / suggested action

### FR7 — Review and canonization
The system must allow insight candidates to be:
- approved
- edited
- rejected
- deferred for more evidence

### FR8 — Sync
The system must sync both evidence and synthesis outputs into durable research storage with explicit provenance.

## 10. Review gates

### Gate 1 — Sampling validity
Question: is the collected sample meaningful for the stated brief, or too biased / too small / too narrow?

### Gate 2 — Cluster validity
Question: are the clustered items truly the same asset, same variant family, or same concept family?

### Gate 3 — Insight validity
Question: does the proposed insight have enough support and properly declared scope?

### Gate 4 — Actionability
Question: is the insight useful enough to translate into a strategic recommendation or test idea?

## 11. Primary outputs

### Output A — Evidence-backed insight cards
Compact, reviewable records with evidence links and confidence.

### Output B — Competitor creative profile
Structured summary of dominant formats, hooks, angles, and repeated tactics per competitor.

### Output C — Trend snapshot
Time-bounded market summary such as rising formats, saturated hooks, and regional deltas.

### Output D — Experiment recommendations
Concrete test suggestions derived from reviewed insights, not from raw model intuition alone.

## 12. V1 scope recommendation

### In scope for V1 (agent-usable pilot)
- one research brief per run
- manifest or handoff-based ingest of a bounded ad set with provenance
- basic normalization and pragmatic dedupe
- representative-asset selection for analysis efficiency
- representative-asset Gemini analysis with strict schema validation
- evidence-backed draft insight synthesis
- workspace-local artifact outputs for every meaningful stage
- pilot-local sync into `logs/market-research/research.db`
- primitives that a parent agent can call independently or compose in a shallow workflow

### Explicitly not required for V1
- a fully integrated authenticated browser collector inside the market research package
- a polished end-to-end CLI/pipeline surface wired into the main app bootstrap
- fully manual review UI or complete approved/rejected/deferred operational workflow
- perfect clustering or market-wide truth claims
- broad longitudinal market intelligence across every source
- performance attribution beyond available evidence

### Deferred after V1
- tighter browser collection automation beyond handoff contracts
- stronger review lifecycle and canonical approved insight storage
- richer repository query/read helpers and retrieval surfaces
- broader enrichment and snapshot layers

## 13. Launch criteria

Agent-usable V1 is ready when the workflow can:

1. validate a defined brief
2. ingest a bounded ad set from manifest/handoff inputs while preserving provenance
3. normalize, dedupe, and cluster that ad set into reviewable intermediate artifacts
4. select representative assets and analyze them with the market-research Gemini schema
5. synthesize evidence-backed draft insights with explicit evidence refs
6. persist artifacts and pilot DB state under the workspace so a parent agent can resume, inspect, or re-run bounded stages
7. support useful parent-agent patterns such as:
   - analyze a fresh export
   - re-synthesize from existing analyses
   - debug one asset or one failed analysis
