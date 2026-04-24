#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

RESULT_KEYS = (
    "ok",
    "action_taken",
    "write_applied",
    "requires_clarification",
    "clarification_reason",
    "pending_prompt_id",
    "canonical_person_key",
    "matched_prompt_id",
    "resolved_update_type",
    "audit_events",
    "errors",
    "data",
    "effective_followup_person_key",
    "routing_reason",
)


def build_result(
    *,
    ok: bool = False,
    action_taken: str = "none",
    write_applied: bool = False,
    requires_clarification: bool = False,
    clarification_reason: str | None = None,
    pending_prompt_id: str | None = None,
    canonical_person_key: str | None = None,
    matched_prompt_id: str | None = None,
    resolved_update_type: str | None = None,
    audit_events: list[str] | None = None,
    errors: list[str] | None = None,
    data: dict[str, Any] | None = None,
    effective_followup_person_key: str | None = None,
    routing_reason: str = "unknown",
) -> dict[str, Any]:
    return {
        "ok": ok,
        "action_taken": action_taken,
        "write_applied": write_applied,
        "requires_clarification": requires_clarification,
        "clarification_reason": clarification_reason,
        "pending_prompt_id": pending_prompt_id,
        "canonical_person_key": canonical_person_key,
        "matched_prompt_id": matched_prompt_id,
        "resolved_update_type": resolved_update_type,
        "audit_events": list(audit_events or []),
        "errors": list(errors or []),
        "data": dict(data or {}),
        "effective_followup_person_key": effective_followup_person_key,
        "routing_reason": routing_reason,
    }


def merge_result(base: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    merged = build_result()
    for key in RESULT_KEYS:
        if key in base:
            merged[key] = base[key]
    for key, value in overrides.items():
        if key in RESULT_KEYS:
            merged[key] = value
        else:
            merged["data"][key] = value
    return merged
