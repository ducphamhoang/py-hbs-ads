#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from common import load_json, save_json, utc_now_iso
from models import PromptRecord

VALID_STATUSES = {"open", "answered", "cancelled", "expired"}


def load_prompts(path: Path) -> list[dict[str, Any]]:
    """Load prompt list from the JSON container file. Returns [] if missing or empty."""
    data = load_json(path, default={"prompts": []})
    return list(data.get("prompts") or [])


def save_prompts(path: Path, prompts: list[dict[str, Any]]) -> None:
    """Write the full prompt container with schema_version, updated_at, and prompts."""
    container: dict[str, Any] = {
        "schema_version": "1.0",
        "updated_at": utc_now_iso(),
        "prompts": prompts,
    }
    save_json(path, container)


def append_prompt(path: Path, prompt: dict[str, Any]) -> None:
    """Append one prompt dict to the store, defaulting status/timestamps if absent."""
    prompts = load_prompts(path)
    entry = dict(prompt)
    entry.setdefault("status", "open")
    entry.setdefault("created_at", utc_now_iso())
    entry["updated_at"] = utc_now_iso()
    prompts.append(entry)
    save_prompts(path, prompts)


def get_open_prompts(path: Path, thread_id: str | None = None) -> list[dict[str, Any]]:
    """Return open prompts, optionally filtered by source.thread_id."""
    prompts = load_prompts(path)
    open_prompts = [p for p in prompts if p.get("status") == "open"]
    if thread_id is not None:
        open_prompts = [
            p for p in open_prompts if (p.get("source") or {}).get("thread_id") == thread_id
        ]
    return open_prompts


def _mark_transition(
    path: Path,
    prompt_id: str,
    new_status: str,
    at: str | None,
    extra: dict[str, Any] | None = None,
) -> bool:
    prompts = load_prompts(path)
    now = at or utc_now_iso()
    found = False
    for prompt in prompts:
        if prompt.get("pending_prompt_id") != prompt_id:
            continue
        prompt["status"] = new_status
        prompt["updated_at"] = now
        prompt["closed_at"] = now
        if extra:
            for key, value in extra.items():
                prompt[key] = value
        found = True
        break
    if found:
        save_prompts(path, prompts)
    return found


def mark_answered(
    path: Path,
    prompt_id: str,
    *,
    resolved_update_type: str | None = None,
    resolved_value: str | None = None,
    resolution_notes: str | None = None,
    at: str | None = None,
) -> bool:
    """Mark a prompt as answered and record resolution metadata. Returns True if found."""
    resolution: dict[str, Any] = {}
    if resolved_update_type is not None:
        resolution["resolved_update_type"] = resolved_update_type
    if resolved_value is not None:
        resolution["resolved_value"] = resolved_value
    if resolution_notes is not None:
        resolution["resolution_notes"] = resolution_notes
    return _mark_transition(
        path,
        prompt_id,
        "answered",
        at,
        extra={"resolution": resolution} if resolution else None,
    )


def mark_cancelled(path: Path, prompt_id: str, *, at: str | None = None) -> bool:
    """Mark a prompt as cancelled. Returns True if found."""
    return _mark_transition(path, prompt_id, "cancelled", at)


def mark_expired(path: Path, prompt_id: str, *, at: str | None = None) -> bool:
    """Mark a prompt as expired. Returns True if found."""
    return _mark_transition(path, prompt_id, "expired", at)


def validate_prompt_schema(prompt: dict[str, Any]) -> list[str]:
    """
    Validate prompt dict structure. Returns a list of error strings.
    Empty list means the prompt is valid.
    """
    errors: list[str] = []
    ppid = prompt.get("pending_prompt_id")
    if not ppid:
        errors.append("missing pending_prompt_id")

    status = prompt.get("status")
    if status not in VALID_STATUSES:
        errors.append(f"invalid status: {status!r} (must be one of {sorted(VALID_STATUSES)})")

    if status == "open":
        source = prompt.get("source") or {}
        notion = prompt.get("notion") or {}
        question = prompt.get("question") or {}
        if not source.get("thread_id"):
            errors.append(f"open prompt {ppid!r} missing source.thread_id")
        if not notion.get("task_id") and not notion.get("project_id"):
            errors.append(f"open prompt {ppid!r} missing notion.task_id and notion.project_id")
        if not question.get("allowed_update_types"):
            errors.append(f"open prompt {ppid!r} missing question.allowed_update_types")

    return errors


def to_prompt_record(prompt: dict[str, Any]) -> PromptRecord:
    return PromptRecord(
        pending_prompt_id=prompt["pending_prompt_id"],
        status=prompt["status"],
        source=prompt.get("source") or {},
        target=prompt.get("target") or {},
        notion=prompt.get("notion") or {},
        created_at=prompt.get("created_at") or "",
        updated_at=prompt.get("updated_at") or "",
        outbound_message=prompt.get("outbound_message"),
        question=prompt.get("question"),
        resolution=prompt.get("resolution"),
        closed_at=prompt.get("closed_at"),
    )
