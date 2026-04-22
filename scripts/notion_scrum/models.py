#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class InboundEvent:
    platform: str
    platform_user_id: str
    text: str
    thread_id: str | None = None
    reply_to_message_id: str | None = None
    canonical_person_key: str | None = None
    display_name: str | None = None


@dataclass
class PromptRecord:
    pending_prompt_id: str
    status: Literal["open", "answered", "cancelled", "expired"]
    source: dict[str, Any]
    target: dict[str, Any]
    notion: dict[str, Any]
    created_at: str
    updated_at: str
    outbound_message: dict[str, Any] | None = None
    question: dict[str, Any] | None = None
    resolution: dict[str, Any] | None = None
    closed_at: str | None = None

    allowed_update_types: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.question and not self.allowed_update_types:
            self.allowed_update_types = list(
                (self.question or {}).get("allowed_update_types") or []
            )


@dataclass
class MatchResult:
    matched: bool
    confidence: float
    requires_clarification: bool
    pending_prompt_id: str | None = None
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    method: str | None = None
    clarification_reason: str | None = None
    candidate_count: int = 0
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UpdatePlan:
    safe_to_apply: bool
    resolved_update_type: str
    pending_prompt_id: str | None = None
    resolved_value: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    confidence: float = 0.0
    reason: str | None = None
    dry_run: bool = False


if __name__ == "__main__":
    InboundEvent(platform="discord", platform_user_id="123", text="hi")
    PromptRecord(
        pending_prompt_id="pp_1",
        status="open",
        source={},
        target={},
        notion={},
        created_at="1970-01-01T00:00:00Z",
        updated_at="1970-01-01T00:00:00Z",
    )
    MatchResult(matched=False, confidence=0.0, requires_clarification=True)
    UpdatePlan(safe_to_apply=False, resolved_update_type="task_comment")
    print("models OK")
