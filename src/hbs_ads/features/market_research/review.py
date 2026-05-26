from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hbs_ads.features.market_research.models import InsightCandidate, ReviewDecision
from hbs_ads.features.market_research.validators import validate_confidence, validate_review_decision


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReviewError(Exception):
    pass


def apply_review(
    insight: InsightCandidate,
    *,
    reviewer: str,
    decision: str,
    rationale: str = "",
    updated_confidence: str = "",
    run_id: str = "",
) -> tuple[InsightCandidate, ReviewDecision]:
    errors: list[str] = []
    if not reviewer or not reviewer.strip():
        errors.append("reviewer cannot be empty")
    errors.extend(validate_review_decision(decision))
    resolved_confidence = updated_confidence or insight.confidence
    errors.extend(validate_confidence(resolved_confidence))
    if errors:
        raise ReviewError("; ".join(errors))

    review_id = f"review_{insight.insight_candidate_id}_{decision}_{uuid.uuid4().hex[:8]}"
    review = ReviewDecision(
        review_id=review_id,
        run_id=run_id or insight.run_id,
        target_type="insight_candidate",
        target_id=insight.insight_candidate_id,
        reviewer=reviewer,
        decision=decision,
        rationale=rationale,
        updated_confidence=resolved_confidence,
        created_at=_now_iso(),
    )

    updated = InsightCandidate(
        insight_candidate_id=insight.insight_candidate_id,
        run_id=insight.run_id,
        insight_type=insight.insight_type,
        title=insight.title,
        signal=insight.signal,
        evidence_summary=insight.evidence_summary,
        scope=insight.scope,
        confidence=resolved_confidence,
        implication=insight.implication,
        evidence_refs=insight.evidence_refs,
        needs_human_review=False,
        status=_decision_to_status(decision),
        created_at=insight.created_at,
    )
    return updated, review


def _decision_to_status(decision: str) -> str:
    mapping = {
        "approve": "approved",
        "approve_with_edits": "approved_with_edits",
        "reject": "rejected",
        "defer_for_more_evidence": "deferred",
    }
    return mapping.get(decision, decision)


def batch_approve(
    insights: list[InsightCandidate],
    *,
    reviewer: str,
    rationale: str = "batch approval",
    run_id: str = "",
) -> tuple[list[InsightCandidate], list[ReviewDecision]]:
    updated_insights: list[InsightCandidate] = []
    reviews: list[ReviewDecision] = []
    for insight in insights:
        updated, review = apply_review(
            insight,
            reviewer=reviewer,
            decision="approve",
            rationale=rationale,
            run_id=run_id,
        )
        updated_insights.append(updated)
        reviews.append(review)
    return updated_insights, reviews
