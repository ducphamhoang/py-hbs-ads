# Representative Asset Selection Policy — Creative Market Research

> **Purpose:** Define how a parent AI agent should choose which asset(s) to analyze from each cluster in a market research sample.

## 1. Why this policy exists

After clustering a collected manifest, the agent faces a practical question:

> “I have 5 variant clusters and 3 concept clusters. Which specific assets should I send to Gemini for analysis?”

Without a clear selection policy:
- agents choose arbitrarily
- duplicate analysis spend increases
- insight quality becomes inconsistent
- audit/review becomes harder

This policy exists to make representative selection **explicit, reviewable, and repeatable**.

## 2. Core framing

### What a “representative asset” is
A representative asset is:
- an asset chosen to **stand in for its cluster** during analysis
- **not necessarily** the best creative
- **not necessarily** the winning ad
- **not necessarily** the most recent upload

It is specifically:
> the asset that best allows an analyst (human or AI) to understand what this cluster is about

### What this policy is NOT
This is not:
- a creative quality ranking
- a performance prediction
- a “best ad” selector

It is:
- an **analysis efficiency + coverage** policy

## 3. Selection goals

When selecting representative assets, the agent should optimize for:

### Goal 1 — Understanding coverage
The selected set should allow the agent to understand:
- dominant hook patterns
- format patterns
- CTA patterns
- angle patterns

across the sample.

### Goal 2 — Cost efficiency
Do not analyze every asset if a smaller representative set can reveal the same patterns.

### Goal 3 — Auditability
Selection decisions should be traceable:
- why this asset was chosen
- why that asset was skipped
- whether multiple assets were needed

### Goal 4 — Robustness
If the best candidate is unusable (corrupt / missing / low-quality), fallback rules should apply gracefully.

## 4. Selection unit hierarchy

Selection happens at two levels:

### Level 1 — Variant cluster selection
Question: within one variant family, which asset represents this family best?

Default rule:
- **1 variant cluster → 1 representative asset** is usually enough
- because variants are near-duplicates or small edits of the same core creative

### Level 2 — Concept cluster selection
Question: within one concept family (multiple variant clusters grouped), how many assets are needed?

Default rule:
- **1 concept cluster → 1–3 representative assets** depending on internal diversity

## 5. Representative selection rules for variant clusters

For each variant cluster, apply these rules in order:

### Rule V1 — Prefer intact local assets
If any member asset has:
- a local file path
- confirmed intact download
- valid duration / format

…prefer that asset over source-URL-only assets.

**Rationale:** local intact assets are more reliable for analysis and reproducible.

---

### Rule V2 — Prefer complete creative structure
Among intact assets, prefer those that appear to have:
- a clear opening/hook region
- a clear body/middle region
- a clear CTA/end region (if CTA is expected for this sample)

Avoid assets that are:
- obviously truncated
- obviously preview-only
- obviously cut mid-scene

**Rationale:** complete creatives yield more meaningful analysis.

---

### Rule V3 — Prefer richer metadata
Among otherwise similar candidates, prefer assets with:
- non-empty `first_seen_at` / `last_seen_at`
- clear `platform` / `geo`
- clear `app_name` / `publisher_name`
- thumbnail available
- landing URL available

**Rationale:** richer metadata helps contextualize analysis and audit later.

---

### Rule V4 — Prefer canonical source representation
If multiple assets are otherwise similar, prefer the one from:
- the primary source for this run (e.g., if most candidates are from `bigspy`, prefer a `bigspy` record)
- the source with the most complete raw_payload

**Rationale:** provenance clarity helps audit and re-run.

---

### Rule V5 — Tie-break by recency
If still tied, prefer the asset with the most recent `last_seen_at`.

**Rationale:** recency often correlates with currently active creative.

---

### Rule V6 — Fallback when best asset is unusable
If the top-choice asset:
- fails download
- is corrupt
- has missing critical fields

…apply the same rules to the next candidate in the ranked order.

If no usable asset exists in the variant cluster:
- mark the cluster as `analysis_blocked`
- record the blocking reason
- do not force analysis on a broken representative

## 6. Representative selection rules for concept clusters

Concept clusters group multiple variant clusters that share a higher-level concept.

For concept clusters, use a slightly different logic:

### Rule C1 — Start with one representative per concept cluster
Default:
- pick the best variant cluster inside the concept cluster
- then pick the best representative asset from that variant cluster

**Rationale:** many concept clusters are homogeneous enough that one asset reveals the core pattern.

---

### Rule C2 — Use multiple representatives when hook/format split exists
If the concept cluster contains variant clusters that differ meaningfully in:
- hook type (e.g., fail-then-win vs direct-benefit)
- format type (e.g., raw-gameplay vs gameplay-plus-overlay)
- CTA style (e.g., direct-download vs reward-claim)

…then select **2–3 representatives** to cover the main splits.

**Rationale:** one asset would under-represent the internal diversity.

---

### Rule C3 — Explicitly record why multiple assets were chosen
When selecting multiple representatives for one concept cluster, record:
- which dimension(s) drove the multi-asset decision
- which representative covers which sub-pattern

**Rationale:** this makes synthesis and review much clearer.

---

### Rule C4 — Cap at 3 representatives per concept cluster unless exceptional
Default cap:
- **max 3 representatives per concept cluster**

Only exceed this cap if:
- the concept cluster is unusually diverse
- the brief explicitly requests deep analysis of this concept family

**Rationale:** diminishing returns beyond 3 assets for one concept.

## 7. Selection output contract

After selection, the agent should produce a structured decision record for each cluster.

### For variant clusters

```json
{
  "variant_cluster_id": "vcl_abc123",
  "selected_asset_id": "asset_xyz789",
  "selection_reason": "intact_local_file,complete_structure,rich_metadata",
  "selection_confidence": "high",
  "fallback_used": false,
  "excluded_asset_ids": ["asset_111", "asset_222"],
  "notes": ""
}
```

### For concept clusters

```json
{
  "concept_cluster_id": "ccl_def456",
  "selected_asset_ids": ["asset_xyz789", "asset_uvw012"],
  "selection_reason": "hook_type_split_within_concept",
  "selection_confidence": "medium",
  "split_dimensions": ["hook_type", "format_type"],
  "max_representatives_cap": 3,
  "fallback_used": false,
  "notes": "Two representatives chosen to cover fail_then_win vs direct_benefit split."
}
```

## 8. Agent workflow pattern

A parent agent should typically:

1. run clustering
2. iterate over variant clusters:
   - apply V1–V6 rules
   - record selection decision
3. iterate over concept clusters:
   - decide whether 1 or 2–3 representatives are needed
   - apply C1–C4 rules
   - record selection decision
4. aggregate selected assets into an analysis queue
5. proceed to analyze only the selected set

## 9. When NOT to analyze a cluster

There are legitimate cases where the agent should **skip analysis** for a cluster:

### Skip condition 1 — No intact asset available
If all member assets are:
- download-failed
- corrupt
- preview-only / thumbnail-only

…mark the cluster as `analysis_blocked` and move on.

### Skip condition 2 — Cluster confidence is too low
If the clustering itself is clearly wrong:
- members share no meaningful similarity
- the cluster appears to be a grouping artifact

…flag it for human review instead of analyzing.

### Skip condition 3 — Sample already saturated
If other clusters already cover the same pattern space densely, and this cluster adds no new dimension, the agent may choose to:
- deprioritize it
- analyze only if budget allows

## 10. Review and audit considerations

Selection decisions should be reviewable:

- which assets were chosen
- which were skipped
- why multiple representatives were used (if applicable)
- whether fallback rules were triggered

This allows humans to:
- override bad selections
- request re-analysis with different representatives
- understand bias in the analyzed sample

## 11. Bottom line

Good representative selection is not about picking the “best ad.”
It is about:

> picking the **most informative asset(s)** for understanding each cluster,
> while minimizing cost and maximizing auditability.

This policy exists to make that tradeoff explicit.
