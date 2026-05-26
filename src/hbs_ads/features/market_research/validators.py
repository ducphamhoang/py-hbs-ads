from __future__ import annotations

from typing import Any

from hbs_ads.features.market_research.models import (
    AdCandidate,
    InsightCandidate,
    ResearchBrief,
)
from hbs_ads.features.market_research.taxonomy import (
    ANALYSIS_SCHEMA_VERSION,
    CONFIDENCE_LEVELS,
    CTA_STYLES,
    FUNNEL_STAGES,
    GAMEPLAY_VISIBILITY,
    HOOK_TYPES,
    FORMAT_TYPES,
    CORE_ANGLES,
    CREATOR_PRESENCE,
    REVIEW_DECISIONS,
)


def _validate_required_string(value: Any, field_name: str) -> list[str]:
    if value is None:
        return [f"{field_name} is required"]
    if isinstance(value, str) and not value.strip():
        return [f"{field_name} cannot be empty"]
    return []


def validate_brief(brief: ResearchBrief) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_required_string(brief.brief_id, "brief_id"))
    errors.extend(_validate_required_string(brief.research_goal, "research_goal"))
    if not brief.market_scope:
        errors.append("market_scope is required")
    if not brief.analysis_focus:
        errors.append("analysis_focus must list at least one dimension")
    errors.extend(_validate_required_string(brief.sampling_strategy, "sampling_strategy"))
    errors.extend(_validate_required_string(brief.output_mode, "output_mode"))
    errors.extend(_validate_required_string(brief.review_mode, "review_mode"))
    return errors


def validate_candidate(candidate: AdCandidate) -> list[str]:
    errors: list[str] = []
    if not candidate.candidate_id:
        errors.append("candidate_id is required")
    if not candidate.run_id:
        errors.append("run_id is required")
    if not candidate.source:
        errors.append("source is required")
    return errors


def validate_analysis_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if payload.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be '{ANALYSIS_SCHEMA_VERSION}', got {payload.get('schema_version')!r}"
        )

    for section in ("observable", "taxonomy_tags", "interpretation", "evidence", "quality"):
        if section not in payload:
            errors.append(f"missing required section: {section}")

    obs = payload.get("observable", {})
    if not isinstance(obs, dict):
        errors.append("observable must be an object")
    else:
        for req_field in (
            "duration_seconds",
            "aspect_ratio",
            "contains_gameplay",
            "gameplay_visibility",
            "creator_presence",
            "text_overlay_present",
            "cta_present",
            "visual_notes",
        ):
            if req_field not in obs:
                errors.append(f"observable.{req_field} is required")
        gv = obs.get("gameplay_visibility")
        if gv not in GAMEPLAY_VISIBILITY:
            errors.append(f"observable.gameplay_visibility must be one of {sorted(GAMEPLAY_VISIBILITY)}, got {gv!r}")
        cp = obs.get("creator_presence")
        if cp not in CREATOR_PRESENCE:
            errors.append(f"observable.creator_presence must be one of {sorted(CREATOR_PRESENCE)}, got {cp!r}")

    tags = payload.get("taxonomy_tags", {})
    if not isinstance(tags, dict):
        errors.append("taxonomy_tags must be an object")
    else:
        for req_tag in ("hook_type", "format_type", "core_angle", "cta_style", "funnel_stage_guess"):
            if req_tag not in tags:
                errors.append(f"taxonomy_tags.{req_tag} is required")
        _check_vocab(errors, "taxonomy_tags.hook_type", tags.get("hook_type"), HOOK_TYPES)
        _check_vocab(errors, "taxonomy_tags.format_type", tags.get("format_type"), FORMAT_TYPES)
        _check_vocab(errors, "taxonomy_tags.core_angle", tags.get("core_angle"), CORE_ANGLES)
        _check_vocab(errors, "taxonomy_tags.cta_style", tags.get("cta_style"), CTA_STYLES)
        _check_vocab(errors, "taxonomy_tags.funnel_stage_guess", tags.get("funnel_stage_guess"), FUNNEL_STAGES)

    interp = payload.get("interpretation", {})
    if not isinstance(interp, dict):
        errors.append("interpretation must be an object")
    else:
        for req_f in ("hypothesized_strategy", "why_it_might_work", "likely_target_player",
                      "competitive_positioning_guess", "novelty_assessment"):
            if req_f not in interp:
                errors.append(f"interpretation.{req_f} is required")

    evidence = payload.get("evidence", [])
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")

    quality = payload.get("quality", {})
    if not isinstance(quality, dict):
        errors.append("quality must be an object")
    else:
        for req_q in ("analysis_confidence", "needs_human_review", "failure_modes"):
            if req_q not in quality:
                errors.append(f"quality.{req_q} is required")

    return errors


def validate_insight_candidate(insight: InsightCandidate) -> list[str]:
    errors: list[str] = []
    if not insight.insight_candidate_id:
        errors.append("insight_candidate_id is required")
    if not insight.run_id:
        errors.append("run_id is required")
    if not insight.title:
        errors.append("title is required")
    if not insight.signal:
        errors.append("signal is required")
    if not insight.evidence_refs:
        errors.append("evidence_refs must not be empty — every insight needs evidence")
    if not insight.scope:
        errors.append("scope must be declared")
    if insight.confidence not in CONFIDENCE_LEVELS:
        errors.append(f"confidence must be one of {sorted(CONFIDENCE_LEVELS)}, got {insight.confidence!r}")
    return errors


def validate_confidence(confidence: str) -> list[str]:
    if confidence not in CONFIDENCE_LEVELS:
        return [f"confidence must be one of {sorted(CONFIDENCE_LEVELS)}, got {confidence!r}"]
    return []


def validate_review_decision(decision: str) -> list[str]:
    if decision not in REVIEW_DECISIONS:
        return [f"decision must be one of {sorted(REVIEW_DECISIONS)}, got {decision!r}"]
    return []


def _check_vocab(errors: list[str], field: str, value: Any, allowed: frozenset[str]) -> None:
    if value is not None and value not in allowed:
        errors.append(f"{field} must be one of {sorted(allowed)}, got {value!r}")
