#!/usr/bin/env python3
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from common import append_jsonl, utc_now_iso


class AuditEventType(Enum):
    IDENTITY_RESOLVED = "identity_resolved"
    IDENTITY_UNRESOLVED = "identity_unresolved"
    NOTION_PERSON_LOOKUP = "notion_person_lookup"
    PROMPT_RECORDED = "prompt_recorded"
    PROMPT_ANSWERED = "prompt_answered"
    PROMPT_CANCELLED = "prompt_cancelled"
    REPLY_MATCHED = "reply_matched"
    REPLY_AMBIGUOUS = "reply_ambiguous"
    UPDATE_PLANNED = "update_planned"
    UPDATE_APPLIED = "update_applied"
    UPDATE_DRY_RUN = "update_dry_run"
    NOTION_WRITE = "notion_write"
    NOTION_WRITE_BLOCKED = "notion_write_blocked"
    STATE_DOCTOR_WARNING = "state_doctor_warning"
    PREFLIGHT_RUN = "preflight_run"


def build_event(event_type: AuditEventType, **kwargs: Any) -> dict[str, Any]:
    """Build an audit record dict with timestamp and event_type merged with caller kwargs."""
    return {"timestamp": utc_now_iso(), "event_type": event_type.value, **kwargs}


def append_event(log_path: Path, event_type: AuditEventType, **kwargs: Any) -> None:
    """Build and append an audit event to the JSONL log at log_path."""
    record = build_event(event_type, **kwargs)
    append_jsonl(log_path, record)
