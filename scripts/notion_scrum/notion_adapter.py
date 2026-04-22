#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from apply_notion_update import apply_update, build_actions
from common import DEFAULT_AUDIT_LOG, DEFAULT_PENDING_PROMPTS, DEFAULT_TEAM_REGISTRY


def plan_actions(
    plan: dict,
    prompt: dict,
    event: dict,
    *,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
) -> list[dict]:
    return build_actions(plan, prompt, event, registry_path=registry_path)


def apply_actions(
    *,
    plan: dict,
    prompt: dict,
    event: dict,
    execute: bool,
    registry_path: Path = DEFAULT_TEAM_REGISTRY,
    state_path: Path = DEFAULT_PENDING_PROMPTS,
    audit_log_path: Path = DEFAULT_AUDIT_LOG,
) -> dict:
    return apply_update(
        plan=plan,
        prompt=prompt,
        event=event,
        execute=execute,
        registry_path=registry_path,
        state_path=state_path,
        audit_log_path=audit_log_path,
    )
