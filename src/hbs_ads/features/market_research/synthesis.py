from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from hbs_ads.features.market_research.models import (
    CreativeAnalysisResult,
    ConceptCluster,
    InsightCandidate,
    ResearchBrief,
    VariantCluster,
)
from hbs_ads.features.market_research.taxonomy import CONFIDENCE_LEVELS


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _insight_id(run_id: str, label: str) -> str:
    raw = f"{run_id}|{label}"
    return "inscand_" + hashlib.sha256(raw.encode()).hexdigest()[:10]


def _confidence_from_count(count: int, total: int) -> str:
    if total == 0:
        return "low"
    ratio = count / total
    if ratio >= 0.4:
        return "high"
    if ratio >= 0.2:
        return "medium"
    return "low"


def synthesize_hook_pattern_insights(
    analyses: list[CreativeAnalysisResult],
    brief: ResearchBrief,
    run_id: str,
) -> list[InsightCandidate]:
    if not analyses:
        return []

    hook_counts: Counter[str] = Counter()
    hook_to_analyses: dict[str, list[str]] = {}
    for a in analyses:
        hook = a.taxonomy_tags.get("hook_type", "unknown")
        hook_counts[hook] += 1
        hook_to_analyses.setdefault(hook, []).append(f"analysis:{a.analysis_id}")

    total = len(analyses)
    insights: list[InsightCandidate] = []

    for hook, count in hook_counts.most_common(5):
        if hook == "unknown":
            continue
        confidence = _confidence_from_count(count, total)
        scope = {
            "geo": brief.market_scope.get("geos", []),
            "platform": brief.market_scope.get("platforms", []),
            "time_window": [
                brief.market_scope.get("date_range", {}).get("start", ""),
                brief.market_scope.get("date_range", {}).get("end", ""),
            ],
        }
        insight = InsightCandidate(
            insight_candidate_id=_insight_id(run_id, f"hook_{hook}"),
            run_id=run_id,
            insight_type="pattern",
            title=f"Hook pattern '{hook}' appears in {count}/{total} analyzed ads",
            signal=f"'{hook}' is one of the repeated hooks in this sample ({count} occurrences out of {total}).",
            evidence_summary={
                "supporting_asset_count": count,
                "sources": list({a.model_provider for a in analyses}),
            },
            scope=scope,
            confidence=confidence,
            implication=(
                f"Consider testing '{hook}' hooks if not already saturated in your own creatives."
                if confidence in ("medium", "high")
                else f"Signal for '{hook}' is weak; gather more data before acting."
            ),
            evidence_refs=hook_to_analyses.get(hook, []),
            needs_human_review=True,
            status="draft",
            created_at=_now_iso(),
        )
        insights.append(insight)

    return insights


def synthesize_format_pattern_insights(
    analyses: list[CreativeAnalysisResult],
    brief: ResearchBrief,
    run_id: str,
) -> list[InsightCandidate]:
    if not analyses:
        return []

    fmt_counts: Counter[str] = Counter()
    fmt_to_analyses: dict[str, list[str]] = {}
    for a in analyses:
        fmt = a.taxonomy_tags.get("format_type", "unknown")
        fmt_counts[fmt] += 1
        fmt_to_analyses.setdefault(fmt, []).append(f"analysis:{a.analysis_id}")

    total = len(analyses)
    insights: list[InsightCandidate] = []

    for fmt, count in fmt_counts.most_common(3):
        if fmt == "unknown":
            continue
        confidence = _confidence_from_count(count, total)
        scope = {
            "geo": brief.market_scope.get("geos", []),
            "platform": brief.market_scope.get("platforms", []),
        }
        insight = InsightCandidate(
            insight_candidate_id=_insight_id(run_id, f"format_{fmt}"),
            run_id=run_id,
            insight_type="pattern",
            title=f"Format '{fmt}' dominates with {count}/{total} occurrences",
            signal=f"'{fmt}' is the most common format in this sample segment.",
            evidence_summary={
                "supporting_asset_count": count,
                "sources": list({a.model_provider for a in analyses}),
            },
            scope=scope,
            confidence=confidence,
            implication=f"Format '{fmt}' appears prevalent. Evaluate differentiation opportunity.",
            evidence_refs=fmt_to_analyses.get(fmt, []),
            needs_human_review=True,
            status="draft",
            created_at=_now_iso(),
        )
        insights.append(insight)

    return insights


def synthesize_insights(
    analyses: list[CreativeAnalysisResult],
    brief: ResearchBrief,
    run_id: str,
    variant_clusters: list[VariantCluster] | None = None,
    concept_clusters: list[ConceptCluster] | None = None,
) -> list[InsightCandidate]:
    insights: list[InsightCandidate] = []
    insights.extend(synthesize_hook_pattern_insights(analyses, brief, run_id))
    insights.extend(synthesize_format_pattern_insights(analyses, brief, run_id))
    return insights
