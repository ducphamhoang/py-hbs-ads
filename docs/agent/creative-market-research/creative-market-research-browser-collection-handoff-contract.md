# Browser-Collection Handoff Contract — Creative Market Research

> **Purpose:** Define the contract between authenticated browser-driven market collection and the downstream creative market research tools in `~/work/py-hbs-ads`.

## 1. Why this contract exists

The market research tool layer is only as good as the handoff it receives from collection.

Without a clear handoff contract, downstream problems show up immediately:
- normalization becomes source-specific guesswork
- provenance is lost
- duplicate detection becomes weaker
- asset analysis cannot be reproduced
- insight claims cannot be audited back to their source

So this contract exists to answer one concrete question:

> When a browser-driven collector finishes gathering ads from an authenticated market tool, what exact shape should it hand to the market research layer?

## 2. Scope

This contract is for:
- authenticated browser collection from market-intelligence tools
- exports or manifests prepared for AI-agent consumption
- handoff into the market research primitives under `~/work/py-hbs-ads/src/hbs_ads/features/market_research/`

This contract is **not** for:
- final research DB schema
- final insight storage schema
- human-facing report formatting

It is specifically the **collection -> research tool handoff layer**.

## 3. Design goals

The handoff contract must be:

1. **source-aware** — preserves which tool/source produced the candidate
2. **provenance-preserving** — keeps enough context to reproduce the query
3. **agent-friendly** — easy for AI agents to inspect and pass into normalization tools
4. **partially tolerant** — can accept missing optional fields without collapsing
5. **strict where it matters** — required fields are genuinely required

## 4. Parent model

The collector side may be:
- a browser tool flow controlled by Hermes
- a separate bounded collector agent
- a human-assisted export step

The downstream consumer is usually:
- a parent orchestrator
- or the `market_research` tool layer

The contract between them should be a **manifest JSON file** with:
- top-level run/query metadata
- candidate records array
- optional asset manifest section
- optional collector notes/errors section

## 5. Recommended handoff artifact paths

Inside the job workspace:

```text
~/work/py-hbs-ads/<job-workspace>/logs/market-research/
  collect/
    candidates.raw.json
    assets-manifest.json
    collection-report.json
```

If the collector only produces one file, the default should be:
- `~/work/py-hbs-ads/<job-workspace>/logs/market-research/collect/candidates.raw.json`

## 6. Top-level manifest shape

Recommended top-level JSON object:

```json
{
  "schema_version": "market-collection-handoff/v1",
  "run_context": {
    "run_id": "run_mr_2026_04_20_idle_us_001",
    "brief_id": "mr_2026_04_20_idle_us_hooks",
    "collected_at": "2026-04-20T12:30:00Z",
    "collector": "browser-agent",
    "source": "market-tool-x",
    "query_context": {
      "geos": ["US"],
      "platforms": ["meta", "tiktok"],
      "date_range": {"start": "2026-04-01", "end": "2026-04-20"},
      "filters": {"genre": "idle"}
    }
  },
  "candidates": [
    {
      "source": "market-tool-x",
      "source_record_id": "ad_001",
      "source_url": "https://example.com/ads/001",
      "app_name": "Idle Kingdom Builder",
      "publisher_name": "Studio Alpha",
      "geo": "US",
      "platform": "meta",
      "first_seen_at": "2026-04-05",
      "last_seen_at": "2026-04-18",
      "asset_url": "https://cdn.example.com/video001.mp4",
      "thumbnail_url": "https://cdn.example.com/thumb001.jpg",
      "landing_url": "https://example.com/store/idle-kingdom",
      "raw_payload": {
        "ad_title": "Build faster now",
        "network": "Meta Ads"
      }
    }
  ],
  "asset_manifest": {
    "downloaded": [],
    "missing": []
  },
  "collection_report": {
    "candidate_count": 1,
    "errors": [],
    "notes": []
  }
}
```

## 7. Required top-level fields

### `schema_version`
Required.

Allowed initial value:
- `market-collection-handoff/v1`

### `run_context`
Required.

Must include:
- `run_id`
- `brief_id` when known
- `collected_at`
- `collector`
- `source`
- `query_context`

### `candidates`
Required.

Must be an array.
Can be empty only if the collection report clearly records why no candidates were captured.

## 8. Candidate record contract

Each entry in `candidates` should represent one raw source-side ad candidate.

### Required candidate fields
These should always be present, even if some values are empty strings:
- `source`
- `source_record_id`
- `source_url`
- `app_name`
- `publisher_name`
- `geo`
- `platform`
- `first_seen_at`
- `last_seen_at`
- `asset_url`
- `thumbnail_url`
- `landing_url`
- `raw_payload`

### Notes on required-but-may-be-empty fields
This contract prefers **present keys with empty values** over silently omitted keys.

Why:
- downstream normalization becomes simpler
- collectors make missingness explicit
- parent agents can distinguish “not collected” from “field forgotten”

## 9. Field semantics

### `source`
The logical market source.
Examples:
- `bigspy`
- `adheart`
- `pipiads`
- `market-tool-x`

Do not use a vague value like `browser`.

### `source_record_id`
The source-native identifier for the ad if available.
If the source has no stable ID, use a durable synthetic identifier and note that in `raw_payload`.

### `source_url`
Direct URL to the source record if available.
Useful for audit and manual review.

### `app_name`
The best available app/game title from the source.
Do not normalize away spelling differences at collection time.
That belongs to downstream normalization.

### `publisher_name`
Raw publisher/advertiser label from the source.
Again, preserve raw form first.

### `geo`
Prefer uppercase ISO-like form where possible, e.g. `US`, `VN`, `KR`.
If the source provides broader region labels, preserve raw value in `raw_payload` too.

### `platform`
Prefer source-facing platform labels at collection time, but keep them simple and recognizable.
Examples:
- `meta`
- `tiktok`
- `youtube`
- `google`

### `first_seen_at` / `last_seen_at`
Preserve source values as collected.
Downstream normalization may convert them.

### `asset_url`
Direct URL or local path reference to the creative asset when available.
If unavailable, keep as empty string and document why in `asset_manifest` or `collection_report`.

### `thumbnail_url`
Optional for downstream logic, but still strongly preferred.
Useful for debugging and light visual review.

### `landing_url`
Landing page or app-store destination if available.

### `raw_payload`
Required object.
This is where source-specific extra fields belong.
Examples:
- ad title
- source network label
- spend/rank indicators if shown
- CTA text snippets
- captured OCR snippets
- source-specific flags

Rule:
- `raw_payload` should preserve what was actually captured
- do not over-normalize it at collection time

## 10. Optional top-level sections

### `asset_manifest`
Recommended when download or local asset materialization was attempted.

Suggested shape:

```json
{
  "downloaded": [
    {
      "candidate_source_record_id": "ad_001",
      "local_path": "/abs/path/to/video001.mp4",
      "mime_type": "video/mp4",
      "download_status": "ok"
    }
  ],
  "missing": [
    {
      "candidate_source_record_id": "ad_002",
      "reason": "source blocked video download"
    }
  ]
}
```

### `collection_report`
Recommended always.

Suggested fields:
- `candidate_count`
- `errors`
- `notes`
- `warnings`
- `auth_state` if relevant

This helps parent agents know whether the collection itself was trustworthy.

## 11. Malformed or partial data rules

### Rule 1 — Prefer partial manifest over silent failure
If collection was incomplete, still write the manifest with:
- collected candidates so far
- explicit errors/warnings
- empty strings for missing fields

### Rule 2 — Never silently invent missing source metadata
If a field was not available, leave it empty and record the condition.

### Rule 3 — Preserve provenance even when asset download fails
A candidate without a downloadable asset may still be useful for scope/distribution analysis.

### Rule 4 — Distinguish missing vs blocked vs not attempted
Use `collection_report` or `asset_manifest` notes so downstream agents know why data is absent.

## 12. Parent-agent acceptance checklist

Before passing a collected manifest into normalization, the parent agent should verify:

- `schema_version` is present
- `run_context.source` is present
- `run_context.query_context` exists
- `candidates` is an array
- every candidate has the required keys, even if some values are empty
- `raw_payload` exists for every candidate
- any missing asset situations are documented somewhere

## 13. Minimal valid manifest example

This is the smallest still-useful form:

```json
{
  "schema_version": "market-collection-handoff/v1",
  "run_context": {
    "run_id": "run_001",
    "brief_id": "brief_001",
    "collected_at": "2026-04-20T12:30:00Z",
    "collector": "browser-agent",
    "source": "market-tool-x",
    "query_context": {"geos": ["US"]}
  },
  "candidates": [
    {
      "source": "market-tool-x",
      "source_record_id": "ad_001",
      "source_url": "https://example.com/ads/001",
      "app_name": "Idle Kingdom Builder",
      "publisher_name": "Studio Alpha",
      "geo": "US",
      "platform": "meta",
      "first_seen_at": "",
      "last_seen_at": "",
      "asset_url": "",
      "thumbnail_url": "",
      "landing_url": "",
      "raw_payload": {}
    }
  ]
}
```

## 14. Recommended collection-side behavior

Collectors should:

1. write one handoff manifest per bounded query/run
2. preserve raw fields rather than normalizing aggressively
3. include source URLs when possible
4. include a collection report even when successful
5. write the manifest before any downstream normalization starts

## 15. Recommended downstream behavior

Downstream parent agents should:

1. validate the handoff contract first
2. only then call normalization tools
3. keep the original raw manifest artifact intact
4. avoid overwriting collected manifests with normalized output

## 16. Bottom line

A good browser-collection handoff is not just “a JSON dump of ads.”
It is:
- reproducible
- provenance-preserving
- explicit about missingness
- easy for AI agents to consume safely

That is the standard this contract is setting.
