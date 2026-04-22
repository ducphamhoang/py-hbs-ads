
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, append_jsonl, load_json, normalize_text, utc_now_iso

SINGLE_CANDIDATE_THRESHOLD = 0.45
HIGH_MARGIN_THRESHOLD = 0.60
HIGH_MARGIN_DELTA = 0.20
EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


def score_candidate(prompt: dict[str, Any], event: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    outbound = prompt.get("outbound_message") or {}
    source = prompt.get("source") or {}
    target = prompt.get("target") or {}
    notion = prompt.get("notion") or {}
    event_text = normalize_text(event.get("text", ""))
    outbound_text = normalize_text(outbound.get("text", ""))

    if event.get("reply_to_message_id") and event.get("reply_to_message_id") == outbound.get("assistant_message_id"):
        score += 0.60
        reasons.append("reply_to_assistant_message")
    if event.get("thread_id") and event.get("thread_id") == source.get("thread_id"):
        score += 0.15
        reasons.append("same_thread")
    if event.get("canonical_person_key") and event.get("canonical_person_key") == target.get("canonical_person_key"):
        score += 0.15
        reasons.append("sender_matches_target")
    if event_text and EMAIL_PATTERN.fullmatch(event_text) and event_text in outbound_text:
        score += 0.20
        reasons.append("listed_choice_mentioned")
    task_title = normalize_text(notion.get("task_title", ""))
    project_title = normalize_text(notion.get("project_title", ""))
    if task_title and task_title in event_text:
        score += 0.08
        reasons.append("task_title_mentioned")
    if project_title and project_title in event_text:
        score += 0.05
        reasons.append("project_title_mentioned")
    return min(score, 1.0), reasons


def match_reply(*, event: dict[str, Any], prompts: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for prompt in prompts:
        score, reasons = score_candidate(prompt, event)
        if score > 0:
            candidates.append({
                "pending_prompt_id": prompt.get("pending_prompt_id"),
                "score": round(score, 4),
                "reasons": reasons,
                "prompt": prompt,
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    result = {
        "matched": False,
        "confidence": 0.0,
        "method": "none",
        "pending_prompt_id": None,
        "candidate_count": len(candidates),
        "candidates": [
            {"pending_prompt_id": c["pending_prompt_id"], "score": c["score"], "reasons": c["reasons"]}
            for c in candidates[:5]
        ],
        "requires_clarification": True,
        "clarification_reason": "no_candidate",
    }

    if len(candidates) == 1 and candidates[0]["score"] >= SINGLE_CANDIDATE_THRESHOLD:
        top = candidates[0]
        method = "reply_to" if "reply_to_assistant_message" in top["reasons"] else "single_candidate"
        result.update({
            "matched": True,
            "confidence": top["score"],
            "method": method,
            "pending_prompt_id": top["pending_prompt_id"],
            "requires_clarification": False,
            "clarification_reason": None,
        })
    elif len(candidates) >= 2:
        top, second = candidates[0], candidates[1]
        if top["score"] >= HIGH_MARGIN_THRESHOLD and top["score"] - second["score"] >= HIGH_MARGIN_DELTA:
            method = "reply_to" if "reply_to_assistant_message" in top["reasons"] else "high_margin"
            result.update({
                "matched": True,
                "confidence": top["score"],
                "method": method,
                "pending_prompt_id": top["pending_prompt_id"],
                "requires_clarification": False,
                "clarification_reason": None,
            })
        else:
            result["clarification_reason"] = "multiple_open_prompts"
    elif len(candidates) == 1:
        result["clarification_reason"] = "single_low_confidence_candidate"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Match inbound reply to pending prompt")
    parser.add_argument("--state", type=Path, default=DEFAULT_PENDING_PROMPTS)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    args = parser.parse_args()

    payload = json.load(sys.stdin)
    event = payload.get("event") or {}
    state = load_json(args.state, default={"prompts": []})
    prompts = [p for p in state.get("prompts", []) if p.get("status") == "open"]
    result = match_reply(event=event, prompts=prompts)

    append_jsonl(args.audit_log, {
        "timestamp": utc_now_iso(),
        "event_type": "reply_matched" if result["matched"] else "reply_ambiguous",
        "pending_prompt_id": result.get("pending_prompt_id"),
        "thread_id": event.get("thread_id"),
        "canonical_person_key": event.get("canonical_person_key"),
        "confidence": result.get("confidence"),
        "method": result.get("method"),
        "clarification_reason": result.get("clarification_reason"),
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
