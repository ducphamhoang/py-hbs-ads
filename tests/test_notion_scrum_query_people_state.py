from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import query_people_state  # noqa: E402


def _state_path(tmp_path: Path) -> Path:
    path = tmp_path / "people_state.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-04-24T00:00:00Z",
                "people": {
                    "ducph": {
                        "availability": {
                            "status": "active",
                            "since": None,
                            "until": None,
                            "timezone": "Asia/Ho_Chi_Minh",
                            "half_day": None,
                            "note": None,
                            "backup_person_key": "toanvt",
                            "source": {},
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "capacity": {
                            "bandwidth": "reduced",
                            "note": "morning only",
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "coordination": {
                            "default_followup_policy": "route_to_backup",
                            "backup_person_key": "toanvt",
                            "last_status_check_at": "2026-04-24T00:00:00Z",
                        },
                        "metadata": {"tags": [], "last_actor_person_key": "ducph"},
                    },
                    "toanvt": {
                        "availability": {
                            "status": "leave",
                            "since": "2026-04-24",
                            "until": "2026-04-28",
                            "timezone": "Asia/Ho_Chi_Minh",
                            "half_day": None,
                            "note": "nghi phep",
                            "backup_person_key": "ducph",
                            "source": {},
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "capacity": {
                            "bandwidth": "normal",
                            "note": None,
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "coordination": {
                            "default_followup_policy": "route_to_backup",
                            "backup_person_key": "ducph",
                            "last_status_check_at": "2026-04-24T00:00:00Z",
                        },
                        "metadata": {"tags": [], "last_actor_person_key": "ducph"},
                    },
                    "hungct": {
                        "availability": {
                            "status": "ooo",
                            "since": "2026-04-24",
                            "until": "2026-04-24",
                            "timezone": "Asia/Ho_Chi_Minh",
                            "half_day": None,
                            "note": None,
                            "backup_person_key": None,
                            "source": {},
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "capacity": {
                            "bandwidth": "limited",
                            "note": "meetings",
                            "updated_at": "2026-04-24T00:00:00Z",
                        },
                        "coordination": {
                            "default_followup_policy": "route_to_backup",
                            "backup_person_key": None,
                            "last_status_check_at": "2026-04-24T00:00:00Z",
                        },
                        "metadata": {"tags": [], "last_actor_person_key": "ducph"},
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_query_person_returns_record_for_canonical_key(tmp_path: Path) -> None:
    path = _state_path(tmp_path)

    result = query_people_state.execute_query(
        state_path=path,
        person="toanvt",
        on_leave_today=False,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )

    assert result["person_key"] == "toanvt"
    assert result["availability"]["status"] == "leave"


def test_query_on_leave_today_returns_leave_and_ooo_people(tmp_path: Path) -> None:
    path = _state_path(tmp_path)

    result = query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=True,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )

    keys = {item["person_key"] for item in result}
    assert keys == {"toanvt", "hungct"}


def test_query_reduced_bandwidth_returns_non_normal_people(tmp_path: Path) -> None:
    path = _state_path(tmp_path)

    result = query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=False,
        reduced_bandwidth=True,
        backup_for=None,
        today="2026-04-24",
    )

    keys = {item["person_key"] for item in result}
    assert keys == {"ducph", "hungct"}


def test_query_backup_for_returns_backup_details_for_canonical_key(tmp_path: Path) -> None:
    path = _state_path(tmp_path)

    result = query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=False,
        reduced_bandwidth=False,
        backup_for="toanvt",
        today="2026-04-24",
    )

    assert result["person_key"] == "toanvt"
    assert result["effective_followup_person_key"] == "ducph"
    assert result["routing_reason"] == "owner_absent_backup_used"


def test_query_missing_file_returns_empty_safe_results(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    person_result = query_people_state.execute_query(
        state_path=path,
        person="toanvt",
        on_leave_today=False,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )
    leave_result = query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=True,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )

    assert person_result["person_key"] == "toanvt"
    assert person_result["found"] is False
    assert leave_result == []


def test_query_modes_are_read_only(tmp_path: Path) -> None:
    path = _state_path(tmp_path)
    before = path.read_text(encoding="utf-8")

    query_people_state.execute_query(
        state_path=path,
        person="toanvt",
        on_leave_today=False,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )
    query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=True,
        reduced_bandwidth=False,
        backup_for=None,
        today="2026-04-24",
    )
    query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=False,
        reduced_bandwidth=True,
        backup_for=None,
        today="2026-04-24",
    )
    query_people_state.execute_query(
        state_path=path,
        person=None,
        on_leave_today=False,
        reduced_bandwidth=False,
        backup_for="toanvt",
        today="2026-04-24",
    )

    assert path.read_text(encoding="utf-8") == before
