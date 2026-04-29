from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "notion_scrum"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import update_people_state  # noqa: E402


def _sample_registry(tmp_path: Path) -> Path:
    path = tmp_path / "team_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-04-24T00:00:00Z",
                "people": {
                    "ducph": {
                        "canonical_person_key": "ducph",
                        "display_name": "DucPH",
                        "aliases": ["ducph", "duc", "ma"],
                    },
                    "toanvt": {
                        "canonical_person_key": "toanvt",
                        "display_name": "ToanVT",
                        "aliases": ["toanvt", "toan", "ma"],
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _empty_state_path(tmp_path: Path) -> Path:
    path = tmp_path / "people_state.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-04-24T00:00:00Z",
                "people": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_build_request_set_leave_defaults_since_to_today() -> None:
    request = update_people_state.build_request(
        person="toan",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup="duc",
        note="nghi phep",
        since=None,
        today="2026-04-24",
    )

    assert request == {
        "person_input": "toan",
        "action": "set-leave",
        "since": "2026-04-24",
        "until": "2026-04-28",
        "bandwidth": None,
        "backup_input": "duc",
        "note": "nghi phep",
    }


def test_build_request_rejects_multiple_write_intents() -> None:
    with pytest.raises(ValueError):
        update_people_state.build_request(
            person="toan",
            action="set-leave",
            until="2026-04-28",
            bandwidth="reduced",
            backup="duc",
            note=None,
            since=None,
            today="2026-04-24",
        )


def test_execute_update_people_state_dry_run_does_not_write(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)
    before = state_path.read_text(encoding="utf-8")

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="toan",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup="duc",
        note="nghi phep",
        since=None,
        execute=False,
        today="2026-04-24",
    )

    assert result["ok"] is True
    assert result["write_applied"] is False
    assert result["canonical_person_key"] == "toanvt"
    assert result["data"]["planned_mutation"]["availability"]["status"] == "leave"
    assert result["data"]["planned_mutation"]["availability"]["note"] == "nghi phep"
    assert state_path.read_text(encoding="utf-8") == before


def test_execute_update_people_state_execute_persists_change(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="toan",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup="duc",
        note="nghi phep",
        since=None,
        execute=True,
        today="2026-04-24",
    )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert result["write_applied"] is True
    assert data["people"]["toanvt"]["availability"]["status"] == "leave"
    assert data["people"]["toanvt"]["availability"]["since"] == "2026-04-24"
    assert data["people"]["toanvt"]["availability"]["until"] == "2026-04-28"


def test_execute_update_people_state_clear_leave(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)

    update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="toan",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup="duc",
        note="nghi phep",
        since=None,
        execute=True,
        today="2026-04-24",
    )
    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="toan",
        action="clear-leave",
        until=None,
        bandwidth=None,
        backup=None,
        note=None,
        since=None,
        execute=True,
        today="2026-04-24",
    )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert data["people"]["toanvt"]["availability"]["status"] == "active"
    assert data["people"]["toanvt"]["availability"]["since"] is None
    assert data["people"]["toanvt"]["availability"]["until"] is None


def test_execute_update_people_state_set_bandwidth(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="duc",
        action="set-bandwidth",
        until=None,
        bandwidth="reduced",
        backup=None,
        note="morning only",
        since=None,
        execute=True,
        today="2026-04-24",
    )

    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert data["people"]["ducph"]["capacity"]["bandwidth"] == "reduced"
    assert data["people"]["ducph"]["capacity"]["note"] == "morning only"


def test_execute_update_people_state_note_is_carried_in_planned_mutation(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="duc",
        action="set-bandwidth",
        until=None,
        bandwidth="limited",
        backup=None,
        note="afternoon only",
        since=None,
        execute=False,
        today="2026-04-24",
    )

    assert result["data"]["planned_mutation"]["capacity"]["note"] == "afternoon only"


def test_execute_update_people_state_ambiguous_person_stops_without_write(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)
    before = state_path.read_text(encoding="utf-8")

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="ma",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup=None,
        note=None,
        since=None,
        execute=True,
        today="2026-04-24",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "target_ambiguous"
    assert result["write_applied"] is False
    assert result["data"]["candidate_records"]
    assert result["data"]["user_hint"]
    assert state_path.read_text(encoding="utf-8") == before


def test_execute_update_people_state_ambiguous_backup_stops_without_write(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)
    before = state_path.read_text(encoding="utf-8")

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="duc",
        action="set-leave",
        until="2026-04-28",
        bandwidth=None,
        backup="ma",
        note=None,
        since=None,
        execute=True,
        today="2026-04-24",
    )

    assert result["ok"] is False
    assert result["action_taken"] == "target_ambiguous"
    assert result["write_applied"] is False
    assert result["data"]["candidate_records"]
    assert result["data"]["user_hint"]
    assert state_path.read_text(encoding="utf-8") == before


def test_result_payload_includes_planned_mutation_details(tmp_path: Path) -> None:
    registry_path = _sample_registry(tmp_path)
    state_path = _empty_state_path(tmp_path)

    result = update_people_state.execute_update_people_state(
        state_path=state_path,
        registry_path=registry_path,
        person="duc",
        action="set-backup",
        until=None,
        bandwidth=None,
        backup="toan",
        note=None,
        since=None,
        execute=False,
        today="2026-04-24",
    )

    assert result["ok"] is True
    assert result["data"]["requested_action"] == "set-backup"
    assert result["data"]["planned_mutation"]["coordination"]["backup_person_key"] == "toanvt"
    assert result["routing_reason"] in {"owner_active", "unknown"}
