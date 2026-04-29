#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

from common import DEFAULT_STATE_DIR, DEFAULT_TEAM_REGISTRY, load_registry
from people_state_store import (
    clear_leave,
    effective_followup_target,
    load_people_state,
    save_people_state,
    set_backup,
    set_bandwidth,
    set_leave,
    validate_people_state,
)
from result_contracts import build_result

DEFAULT_PEOPLE_STATE = DEFAULT_STATE_DIR / "people_state.json"
VALID_ACTIONS = ("set-leave", "clear-leave", "set-bandwidth", "set-backup")


def _today_iso(today: str | None = None) -> str:
    return today or date.today().isoformat()


def _normalize_lookup(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _candidate_record(person: dict[str, Any], canonical_key: str) -> dict[str, Any]:
    return {
        "canonical_person_key": canonical_key,
        "display_name": person.get("display_name"),
        "aliases": list(person.get("aliases") or []),
    }


def _build_not_found_result(*, field_name: str, raw_value: str) -> dict[str, Any]:
    return build_result(
        ok=False,
        action_taken="target_not_found",
        write_applied=False,
        errors=[f"No registry match for {field_name}={raw_value!r}."],
        data={
            "field_name": field_name,
            "lookup_value": raw_value,
            "candidate_records": [],
            "user_hint": f"Provide a canonical person key or a known alias for {field_name}.",
        },
    )


def _build_ambiguity_result(*, field_name: str, raw_value: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return build_result(
        ok=False,
        action_taken="target_ambiguous",
        write_applied=False,
        errors=[f"Ambiguous {field_name}={raw_value!r}; multiple registry matches found."],
        data={
            "field_name": field_name,
            "lookup_value": raw_value,
            "candidate_records": candidates,
            "user_hint": f"{field_name} is ambiguous; provide a canonical person key.",
        },
    )


def resolve_person_input(
    *,
    registry: dict[str, Any],
    raw_value: str,
    field_name: str,
) -> dict[str, Any]:
    normalized = _normalize_lookup(raw_value)
    candidates: list[dict[str, Any]] = []

    for canonical_key, person in (registry.get("people") or {}).items():
        aliases = {
            _normalize_lookup(canonical_key),
            _normalize_lookup(person.get("canonical_person_key") or canonical_key),
            _normalize_lookup(person.get("display_name") or ""),
        }
        aliases.update(_normalize_lookup(alias) for alias in (person.get("aliases") or []))
        aliases.discard("")
        if normalized in aliases:
            candidates.append(_candidate_record(person, canonical_key))

    if not candidates:
        return _build_not_found_result(field_name=field_name, raw_value=raw_value)
    if len(candidates) > 1:
        return _build_ambiguity_result(field_name=field_name, raw_value=raw_value, candidates=candidates)

    candidate = candidates[0]
    return build_result(
        ok=True,
        action_taken="target_resolved",
        write_applied=False,
        canonical_person_key=candidate["canonical_person_key"],
        data={
            "field_name": field_name,
            "lookup_value": raw_value,
            "candidate_records": candidates,
        },
    )


def build_request(
    *,
    person: str | None,
    action: str | None,
    until: str | None,
    bandwidth: str | None,
    backup: str | None,
    note: str | None,
    since: str | None,
    today: str | None = None,
) -> dict[str, Any]:
    if not person:
        raise ValueError("--person is required")
    if action not in VALID_ACTIONS:
        raise ValueError(f"--action must be one of: {', '.join(VALID_ACTIONS)}")

    action_fields = {
        "set-leave": {"until", "backup", "note"},
        "clear-leave": set(),
        "set-bandwidth": {"bandwidth", "note"},
        "set-backup": {"backup"},
    }
    provided_fields = {name for name, value in {"until": until, "bandwidth": bandwidth, "backup": backup, "note": note}.items() if value is not None}
    allowed_fields = action_fields[action]
    disallowed_fields = provided_fields - allowed_fields
    if disallowed_fields:
        raise ValueError(
            f"Provide exactly one update intent. Fields {sorted(disallowed_fields)} do not apply to action {action!r}."
        )

    if action == "set-leave":
        if until is None:
            raise ValueError("set-leave requires --until")
        return {
            "person_input": person,
            "action": action,
            "since": since or _today_iso(today),
            "until": until,
            "bandwidth": None,
            "backup_input": backup,
            "note": note,
        }

    if action == "clear-leave":
        return {
            "person_input": person,
            "action": action,
            "since": None,
            "until": None,
            "bandwidth": None,
            "backup_input": None,
            "note": None,
        }

    if action == "set-bandwidth":
        if bandwidth is None:
            raise ValueError("set-bandwidth requires --bandwidth")
        return {
            "person_input": person,
            "action": action,
            "since": None,
            "until": None,
            "bandwidth": bandwidth,
            "backup_input": None,
            "note": note,
        }

    if backup is None:
        raise ValueError("set-backup requires --backup")
    return {
        "person_input": person,
        "action": action,
        "since": None,
        "until": None,
        "bandwidth": None,
        "backup_input": backup,
        "note": None,
    }


def _source_payload(action: str, execute: bool) -> dict[str, Any]:
    return {
        "kind": "manual_command",
        "tool": "update_people_state",
        "action": action,
        "mode": "execute" if execute else "dry_run",
    }


def _plan_mutation(
    *,
    state: dict[str, Any],
    person_key: str,
    request: dict[str, Any],
    backup_key: str | None,
    execute: bool,
) -> dict[str, Any]:
    mutated = copy.deepcopy(state)
    action = request["action"]
    source = _source_payload(action, execute)

    if action == "set-leave":
        return set_leave(
            mutated,
            person_key,
            request["since"],
            request["until"],
            backup_key,
            request["note"],
            source,
        )
    if action == "clear-leave":
        return clear_leave(mutated, person_key, source)
    if action == "set-bandwidth":
        return set_bandwidth(mutated, person_key, request["bandwidth"], request["note"], source)
    return set_backup(mutated, person_key, backup_key or "", source)


def _validation_result(errors: list[str], *, person_key: str, request: dict[str, Any]) -> dict[str, Any]:
    return build_result(
        ok=False,
        action_taken="validation_failed",
        write_applied=False,
        canonical_person_key=person_key,
        errors=errors,
        data={
            "requested_action": request["action"],
            "resolved_person_key": person_key,
        },
    )


def execute_update_people_state(
    *,
    state_path: str | Path,
    registry_path: str | Path,
    person: str | None,
    action: str | None,
    until: str | None,
    bandwidth: str | None,
    backup: str | None,
    note: str | None,
    since: str | None = None,
    execute: bool = False,
    today: str | None = None,
) -> dict[str, Any]:
    request = build_request(
        person=person,
        action=action,
        until=until,
        bandwidth=bandwidth,
        backup=backup,
        note=note,
        since=since,
        today=today,
    )

    registry = load_registry(Path(registry_path))
    person_result = resolve_person_input(
        registry=registry,
        raw_value=request["person_input"],
        field_name="person",
    )
    if not person_result["ok"]:
        return person_result
    person_key = person_result["canonical_person_key"]

    backup_key = None
    if request["backup_input"] is not None:
        backup_result = resolve_person_input(
            registry=registry,
            raw_value=request["backup_input"],
            field_name="backup",
        )
        if not backup_result["ok"]:
            return backup_result
        backup_key = backup_result["canonical_person_key"]

    state = load_people_state(Path(state_path))
    planned_state = _plan_mutation(
        state=state,
        person_key=person_key,
        request=request,
        backup_key=backup_key,
        execute=execute,
    )

    errors = validate_people_state(planned_state, registry=registry)
    if errors:
        return _validation_result(errors, person_key=person_key, request=request)

    followup_person_key, routing_reason = effective_followup_target(planned_state, person_key)
    planned_person = copy.deepcopy((planned_state.get("people") or {}).get(person_key) or {})
    data = {
        "requested_action": request["action"],
        "resolved_person_key": person_key,
        "resolved_backup_key": backup_key,
        "requested_inputs": {
            "person": request["person_input"],
            "backup": request["backup_input"],
            "until": request["until"],
            "bandwidth": request["bandwidth"],
            "note": request["note"],
        },
        "planned_mutation": planned_person,
        "effective_followup_target": followup_person_key,
    }

    if execute:
        save_people_state(Path(state_path), planned_state)

    return build_result(
        ok=True,
        action_taken="write_applied" if execute else "dry_run_ready",
        write_applied=execute,
        canonical_person_key=person_key,
        resolved_update_type=request["action"],
        data=data,
        effective_followup_person_key=followup_person_key,
        routing_reason=routing_reason,
    )


def _run_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return execute_update_people_state(
        state_path=args.state,
        registry_path=args.registry,
        person=args.person,
        action=args.action,
        until=args.until,
        bandwidth=args.bandwidth,
        backup=args.backup,
        note=args.note,
        execute=args.execute,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Guarded operator CLI for local people-state updates")
    parser.add_argument("--state", type=Path, default=DEFAULT_PEOPLE_STATE)
    parser.add_argument("--registry", type=Path, default=DEFAULT_TEAM_REGISTRY)
    parser.add_argument("--person", required=True)
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS)
    parser.add_argument("--until")
    parser.add_argument("--bandwidth")
    parser.add_argument("--backup")
    parser.add_argument("--note")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    try:
        result = _run_from_args(args)
    except ValueError as exc:
        result = build_result(
            ok=False,
            action_taken="invalid_request",
            write_applied=False,
            errors=[str(exc)],
            data={"user_hint": "Adjust the flags so the request contains one valid write intent."},
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
