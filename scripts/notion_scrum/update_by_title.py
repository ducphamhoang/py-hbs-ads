#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from board_cache import DEFAULT_BOARD_CACHE, load_snapshot
from resolve_prepare_apply_patch import apply_patch_from_resolved_target

_STATUS_PATTERN = re.compile(
    r"^\s*set\s+(task|project)\s+(.+?)(?:\s+of\s+project\s+(.+?))?\s+to\s+(.+?)\s*$",
    re.IGNORECASE,
)
_STATUS_PATTERN_VI = re.compile(
    r"^\s*đổi\s+status\s+(task|project)\s+(.+?)(?:\s+của\s+project\s+(.+?))?\s+thành\s+(.+?)\s*$",
    re.IGNORECASE,
)
_BLOCK_PATTERN = re.compile(
    r"^\s*block\s+(task|project)\s+(.+?)(?:\s+of\s+project\s+(.+?))?\s+because\s+(.+?)\s*$",
    re.IGNORECASE,
)
_BLOCK_PATTERN_VI = re.compile(
    r"^\s*đánh\s+dấu\s+blocked\s+(task|project)\s+(.+?)(?:\s+của\s+project\s+(.+?))?\s+vì\s+(.+?)\s*$",
    re.IGNORECASE,
)
_DUE_DATE_PATTERN = re.compile(
    r"^\s*set\s+due\s+date\s+of\s+(task|project)\s+(.+?)(?:\s+of\s+project\s+(.+?))?\s+to\s+(.+?)\s*$",
    re.IGNORECASE,
)
_DUE_DATE_PATTERN_VI = re.compile(
    r"^\s*đặt\s+due\s+date\s+(task|project)\s+(.+?)(?:\s+của\s+project\s+(.+?))?\s+là\s+(.+?)\s*$",
    re.IGNORECASE,
)
_NOTE_PATTERN = re.compile(
    r"^\s*note\s+on\s+(task|project)\s+(.+?)(?:\s+of\s+project\s+(.+?))?\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_NOTE_PATTERN_VI = re.compile(
    r"^\s*ghi\s+note\s+cho\s+(task|project)\s+(.+?)(?:\s+của\s+project\s+(.+?))?\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def _kind_to_target(kind_raw: str) -> str:
    return "tasks" if kind_raw.lower() == "task" else "projects"


def _normalize_date_input(value: str) -> str:
    text = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        normalized = text
    elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        day, month, year = text.split("/")
        normalized = f"{year}-{month}-{day}"
    elif re.fullmatch(r"\d{4}/\d{2}/\d{2}", text):
        year, month, day = text.split("/")
        normalized = f"{year}-{month}-{day}"
    else:
        raise ValueError(f"Unsupported date format: {value!r}. Use YYYY-MM-DD or DD/MM/YYYY")
    date.fromisoformat(normalized)
    return normalized


def _build_block_request(kind_raw: str, title: str, project_title: str | None, reason_text: str) -> dict[str, Any]:
    reason = (reason_text or "").strip()
    if not reason:
        raise ValueError("blocked_reason must be non-empty")
    return {
        "target_kind": _kind_to_target(kind_raw),
        "title": title.strip(),
        "project_title": project_title or None,
        "patch_kind": "multi",
        "patch_variables": {
            "patches": [
                {"kind": "status", "variables": {"status_name": "Blocked"}},
                {"kind": "rich-text", "variables": {"property_name": "Blocked reason", "text": reason}},
            ]
        },
    }


def parse_instruction(instruction: str) -> dict[str, Any]:
    text = (instruction or "").strip()

    status_match = _STATUS_PATTERN.match(text) or _STATUS_PATTERN_VI.match(text)
    if status_match:
        kind_raw, title, project_title, status_name = status_match.groups()
        return {
            "target_kind": _kind_to_target(kind_raw),
            "title": title.strip(),
            "project_title": (project_title or None),
            "patch_kind": "status",
            "patch_variables": {"status_name": status_name.strip()},
        }

    block_match = _BLOCK_PATTERN.match(text) or _BLOCK_PATTERN_VI.match(text)
    if block_match:
        kind_raw, title, project_title, reason_text = block_match.groups()
        return _build_block_request(kind_raw, title, project_title, reason_text)

    due_match = _DUE_DATE_PATTERN.match(text) or _DUE_DATE_PATTERN_VI.match(text)
    if due_match:
        kind_raw, title, project_title, due_date = due_match.groups()
        target_kind = _kind_to_target(kind_raw)
        # Projects use "End date", Tasks use "Due date"
        date_property = "End date" if target_kind == "projects" else "Due date"
        return {
            "target_kind": target_kind,
            "title": title.strip(),
            "project_title": (project_title or None),
            "patch_kind": "date",
            "patch_variables": {"property_name": date_property, "date_start": _normalize_date_input(due_date)},
        }

    note_match = _NOTE_PATTERN.match(text) or _NOTE_PATTERN_VI.match(text)
    if note_match:
        kind_raw, title, project_title, note_text = note_match.groups()
        return {
            "target_kind": _kind_to_target(kind_raw),
            "title": title.strip(),
            "project_title": (project_title or None),
            "patch_kind": "rich-text",
            "patch_variables": {"property_name": "Notes", "text": note_text.strip()},
        }

    raise ValueError(
        "Unsupported instruction format. Expected one of: "
        "'set task <title> of project <project title> to <status>', "
        "'set due date of task <title> of project <project title> to YYYY-MM-DD', "
        "'note on task <title> of project <project title>: <text>', "
        "or Vietnamese equivalents like 'đổi status task ... thành ...', 'đặt due date task ... là ...', 'ghi note cho task ...: ...'"
    )


def build_request(
    *,
    instruction: str | None,
    target_kind: str | None,
    title: str | None,
    project_title: str | None,
    status: str | None,
    due_date: str | None,
    note: str | None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    if instruction:
        return parse_instruction(instruction)
    intents = [value is not None for value in (status, due_date, note, blocked_reason)]
    if sum(intents) != 1:
        raise ValueError("Provide exactly one update intent: status, due_date, note, or blocked_reason")
    if not target_kind or not title:
        raise ValueError("target_kind and title are required when not using free-text instruction")
    if status is not None:
        return {
            "target_kind": target_kind,
            "title": title,
            "project_title": project_title,
            "patch_kind": "status",
            "patch_variables": {"status_name": status},
        }
    if due_date is not None:
        # Projects use "End date", Tasks use "Due date"
        date_property = "End date" if target_kind == "projects" else "Due date"
        return {
            "target_kind": target_kind,
            "title": title,
            "project_title": project_title,
            "patch_kind": "date",
            "patch_variables": {"property_name": date_property, "date_start": _normalize_date_input(due_date)},
        }
    if note is not None:
        return {
            "target_kind": target_kind,
            "title": title,
            "project_title": project_title,
            "patch_kind": "rich-text",
            "patch_variables": {"property_name": "Notes", "text": note or ""},
        }
    return _build_block_request("task" if target_kind == "tasks" else "project", title, project_title, blocked_reason or "")


def execute_update_by_title(
    *,
    snapshot: dict[str, Any],
    instruction: str | None,
    target_kind: str | None,
    title: str | None,
    project_title: str | None,
    status: str | None,
    due_date: str | None,
    note: str | None,
    resolve_mode: str,
    max_cache_age_seconds: int,
    execute: bool,
    now_iso: str | None = None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    request = build_request(
        instruction=instruction,
        target_kind=target_kind,
        title=title,
        project_title=project_title,
        status=status,
        due_date=due_date,
        note=note,
        blocked_reason=blocked_reason,
    )
    result = apply_patch_from_resolved_target(
        snapshot=snapshot,
        target_kind=request["target_kind"],
        title=request["title"],
        project_title=request.get("project_title"),
        patch_kind=request["patch_kind"],
        patch_variables=request["patch_variables"],
        resolve_mode=resolve_mode,
        max_cache_age_seconds=max_cache_age_seconds,
        execute=execute,
        now_iso=now_iso,
    )
    if not result.get("ok") and result.get("action_taken") == "target_ambiguous":
        data = dict(result.get("data") or {})
        data.setdefault("user_hint", data.get("ambiguity_message") or "Task/project is ambiguous; provide more context.")
        result["data"] = data
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator-friendly cache-backed update by title")
    parser.add_argument("--cache", type=Path, default=DEFAULT_BOARD_CACHE)
    parser.add_argument("--instruction", help="Free-text instruction, e.g. set task X of project Y to In progress")
    parser.add_argument("--target-kind", choices=["tasks", "projects"])
    parser.add_argument("--title")
    parser.add_argument("--project-title")
    parser.add_argument("--status")
    parser.add_argument("--due-date")
    parser.add_argument("--note")
    parser.add_argument("--blocked-reason")
    parser.add_argument("--resolve-mode", choices=["auto", "safe", "fast"], default="auto")
    parser.add_argument("--max-cache-age-seconds", type=int, default=900)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    snapshot = load_snapshot(args.cache)
    result = execute_update_by_title(
        snapshot=snapshot,
        instruction=args.instruction,
        target_kind=args.target_kind,
        title=args.title,
        project_title=args.project_title,
        status=args.status,
        due_date=args.due_date,
        note=args.note,
        blocked_reason=args.blocked_reason,
        resolve_mode=args.resolve_mode,
        max_cache_age_seconds=args.max_cache_age_seconds,
        execute=args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
