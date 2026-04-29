#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from common import DEFAULT_STATE_DIR
from people_state_store import (
    effective_followup_target,
    get_person_state,
    is_person_absent,
    load_people_state,
)

DEFAULT_PEOPLE_STATE = DEFAULT_STATE_DIR / "people_state.json"


def _today_iso(today: str | None = None) -> str:
    return today or date.today().isoformat()


def _date_in_window(target_day: str, since: str | None, until: str | None) -> bool:
    if since and target_day < since:
        return False
    if until and target_day > until:
        return False
    return True


def query_person(data: dict[str, Any], person_key: str) -> dict[str, Any]:
    person = get_person_state(data, person_key)
    if person is None:
        return {"person_key": person_key, "found": False}
    return {"person_key": person_key, "found": True, **person}


def query_on_leave_today(data: dict[str, Any], *, today: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for person_key in sorted(data.get("people", {})):
        person = get_person_state(data, person_key)
        if person is None or not is_person_absent(data, person_key):
            continue
        availability = person.get("availability", {})
        if not _date_in_window(today, availability.get("since"), availability.get("until")):
            continue
        results.append(
            {
                "person_key": person_key,
                "availability": availability,
                "capacity": person.get("capacity", {}),
                "coordination": person.get("coordination", {}),
                "metadata": person.get("metadata", {}),
            }
        )
    return results


def query_reduced_bandwidth(data: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for person_key in sorted(data.get("people", {})):
        person = get_person_state(data, person_key)
        if person is None:
            continue
        capacity = person.get("capacity", {})
        if capacity.get("bandwidth", "unknown") == "normal":
            continue
        results.append(
            {
                "person_key": person_key,
                "availability": person.get("availability", {}),
                "capacity": capacity,
                "coordination": person.get("coordination", {}),
                "metadata": person.get("metadata", {}),
            }
        )
    return results


def query_backup_for(data: dict[str, Any], person_key: str) -> dict[str, Any]:
    person = get_person_state(data, person_key)
    target_person_key, routing_reason = effective_followup_target(data, person_key)
    if person is None:
        return {
            "person_key": person_key,
            "found": False,
            "effective_followup_person_key": target_person_key,
            "routing_reason": routing_reason,
        }

    availability = person.get("availability", {})
    coordination = person.get("coordination", {})
    return {
        "person_key": person_key,
        "found": True,
        "availability_backup_person_key": availability.get("backup_person_key"),
        "coordination_backup_person_key": coordination.get("backup_person_key"),
        "effective_followup_person_key": target_person_key,
        "routing_reason": routing_reason,
    }


def execute_query(
    *,
    state_path: str | Path,
    person: str | None,
    on_leave_today: bool,
    reduced_bandwidth: bool,
    backup_for: str | None,
    today: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    requested_modes = [
        person is not None,
        on_leave_today,
        reduced_bandwidth,
        backup_for is not None,
    ]
    if sum(requested_modes) != 1:
        raise ValueError(
            "Provide exactly one query mode: --person, --on-leave-today, --reduced-bandwidth, or --backup-for"
        )

    data = load_people_state(state_path)
    if person is not None:
        return query_person(data, person)
    if on_leave_today:
        return query_on_leave_today(data, today=_today_iso(today))
    if reduced_bandwidth:
        return query_reduced_bandwidth(data)
    if backup_for is not None:
        return query_backup_for(data, backup_for)
    raise ValueError("No query mode selected")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect local people-state staffing data")
    parser.add_argument("--state", type=Path, default=DEFAULT_PEOPLE_STATE)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--person")
    group.add_argument("--on-leave-today", action="store_true")
    group.add_argument("--reduced-bandwidth", action="store_true")
    group.add_argument("--backup-for")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = execute_query(
        state_path=args.state,
        person=args.person,
        on_leave_today=args.on_leave_today,
        reduced_bandwidth=args.reduced_bandwidth,
        backup_for=args.backup_for,
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
