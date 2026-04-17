from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hbs_ads.cli.main import main


def _bootstrap_workspace(tmp_path: Path) -> None:
    assert main(["--workspace", str(tmp_path), "init", "workspace"]) == 0
    assert main(["--workspace", str(tmp_path), "init", "db"]) == 0


def _approve_ingested_clip(tmp_path: Path, filename: str) -> None:
    (tmp_path / "inbox" / filename).write_text("fake media", encoding="utf-8")
    assert main(["--workspace", str(tmp_path), "ingest", "run"]) == 0
    _write_analysis_fixture(tmp_path, filename)
    assert main(["--workspace", str(tmp_path), "tag", "auto"]) == 0
    assert main(["--workspace", str(tmp_path), "tag", "ai"]) == 0
    assert main(["--workspace", str(tmp_path), "tag", "approve", "--all"]) == 0


def _write_analysis_fixture(tmp_path: Path, filename: str, *, confidence: str = "medium") -> None:
    clip_path = tmp_path / "_ASSETS" / "raw" / filename
    payload = {
        "concept": "build",
        "vibe": "upbeat",
        "style": "2d",
        "has_sfx": True,
        "text_on_screen": "Play now",
        "notes": f"fixture analysis for {filename}",
        "confidence": confidence,
        "cta_present": "cta" in filename or "offer" in filename or "hook" in filename,
        "cta_text": "Play now",
        "cta_start_seconds": 8.5,
        "cta_end_seconds": 12.0,
        "total_duration_seconds": 12.0,
    }
    clip_path.with_name(f"{clip_path.name}.analysis.json").write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )


def test_ingest_real_run_copies_file_and_registers_clip(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    source = tmp_path / "inbox" / "sample.mp4"
    source.write_text("fake media", encoding="utf-8")

    assert main(["--workspace", str(tmp_path), "ingest", "run"]) == 0
    captured = capsys.readouterr()
    assert "ingest completed" in captured.out
    destination = tmp_path / "_ASSETS" / "raw" / "sample.mp4"
    assert destination.exists()

    with sqlite3.connect(tmp_path / "clips.db") as conn:
        row = conn.execute("SELECT kind, status FROM clips WHERE path = ?", (str(destination),)).fetchone()
    assert row == ("raw", "ingested")


def test_trim_run_and_clip_support_dry_run(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    clip_input = tmp_path / "_ASSETS" / "raw" / "source.mp4"
    clip_input.parent.mkdir(parents=True, exist_ok=True)
    clip_input.write_text("fake media", encoding="utf-8")
    config_path = tmp_path / "cuts.json"
    config_path.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "input": str(clip_input),
                        "from": "00:00:01",
                        "to": "00:00:02",
                        "name": "first-cut",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert main(
        ["--workspace", str(tmp_path), "trim", "run", "--config", str(config_path), "--dry-run"]
    ) == 0
    captured = capsys.readouterr()
    assert "trim run planned" in captured.out

    assert main(
        [
            "--workspace",
            str(tmp_path),
            "trim",
            "clip",
            "--input",
            str(clip_input),
            "--from",
            "00:00:01",
            "--to",
            "00:00:02",
            "--name",
            "second-cut",
            "--dry-run",
        ]
    ) == 0
    captured = capsys.readouterr()
    assert "trim clip planned" in captured.out


def test_tagging_round_trip_updates_clip_state(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    source = tmp_path / "inbox" / "hero_blast.mp4"
    source.write_text("fake media", encoding="utf-8")
    assert main(["--workspace", str(tmp_path), "ingest", "run"]) == 0
    _write_analysis_fixture(tmp_path, "hero_blast.mp4")

    assert main(["--workspace", str(tmp_path), "tag", "auto"]) == 0
    assert main(["--workspace", str(tmp_path), "tag", "ai"]) == 0
    assert main(["--workspace", str(tmp_path), "tag", "pending"]) == 0
    pending_output = capsys.readouterr().out
    assert "tag pending found 1 clips" in pending_output

    assert main(["--workspace", str(tmp_path), "tag", "approve", "--all"]) == 0
    with sqlite3.connect(tmp_path / "clips.db") as conn:
        row = conn.execute(
            "SELECT approved, status, tags_json, confidence, gemini_tagged, analysis_json FROM clips"
        ).fetchone()
    assert row is not None
    assert row[0] == 1
    assert row[1] == "approved"
    assert "ai-reviewed" in row[2]
    assert row[3] == "medium"
    assert row[4] == 1
    assert json.loads(row[5])["cta_start_seconds"] == 8.5


def test_variants_round_trip_creates_configs_outputs_and_archive(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    _approve_ingested_clip(tmp_path, "hook-question.mp4")
    _approve_ingested_clip(tmp_path, "body-offer.mp4")

    assert main(["--workspace", str(tmp_path), "variants", "generate", "--max-body", "1"]) == 0
    generated_output = capsys.readouterr().out
    assert "variants generate completed" in generated_output

    configs = sorted((tmp_path / "generated_variants").glob("*.json"))
    assert configs
    assert main(
        [
            "--workspace",
            str(tmp_path),
            "variants",
            "assemble",
            "--config",
            str(configs[0]),
        ]
    ) == 0
    assemble_output = capsys.readouterr().out
    assert "variants assemble completed" in assemble_output

    with sqlite3.connect(tmp_path / "clips.db") as conn:
        variant_name = conn.execute("SELECT name FROM variants ORDER BY name LIMIT 1").fetchone()[0]

    assert main(
        ["--workspace", str(tmp_path), "variants", "export", "--variant", variant_name]
    ) == 0
    assert "variants export completed" in capsys.readouterr().out

    assert main(
        ["--workspace", str(tmp_path), "variants", "validate", "--platform", "tiktok"]
    ) == 0
    assert "variants validate completed" in capsys.readouterr().out

    assert main(
        ["--workspace", str(tmp_path), "variants", "archive", "--variant", variant_name]
    ) == 0
    assert "variants archive completed" in capsys.readouterr().out

    export_path = tmp_path / "VARIANTS" / variant_name / "export" / f"{variant_name}.mp4"
    validation_path = tmp_path / "VARIANTS" / variant_name / "validation-tiktok.json"
    archive_path = tmp_path / "archive" / variant_name
    assert export_path.exists()
    assert validation_path.exists()
    assert archive_path.exists()


def test_hooks_assemble_creates_hook_asset_from_approved_clip(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    _approve_ingested_clip(tmp_path, "hook-question.mp4")

    assert main(
        ["--workspace", str(tmp_path), "hooks", "assemble", "--name", "hook-question"]
    ) == 0
    output = capsys.readouterr().out
    assert "hooks assemble completed" in output

    hook_output = tmp_path / "_HOOKS" / "hook-question.mp4"
    assert hook_output.exists()
    with sqlite3.connect(tmp_path / "clips.db") as conn:
        row = conn.execute("SELECT kind, status FROM clips WHERE path = ?", (str(hook_output),)).fetchone()
    assert row == ("hook", "hook-assembled")


def test_pipeline_run_blocks_until_review_gate_then_completes(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    (tmp_path / "inbox" / "body-offer.mp4").write_text("fake media", encoding="utf-8")
    assert main(["--workspace", str(tmp_path), "ingest", "run"]) == 0
    _write_analysis_fixture(tmp_path, "body-offer.mp4")

    assert main(["--workspace", str(tmp_path), "pipeline", "run", "--ingest"]) == 0
    capsys.readouterr()

    assert main(["--workspace", str(tmp_path), "pipeline", "run"]) == 0
    blocked_output = capsys.readouterr().out
    assert "pipeline run blocked at review gate" in blocked_output

    assert main(["--workspace", str(tmp_path), "tag", "approve", "--all"]) == 0
    assert main(["--workspace", str(tmp_path), "pipeline", "run"]) == 0
    completed_output = capsys.readouterr().out
    assert "pipeline run completed in full mode" in completed_output

    with sqlite3.connect(tmp_path / "clips.db") as conn:
        variants = conn.execute("SELECT name, status FROM variants ORDER BY name").fetchall()
    assert variants
    for name, status in variants:
        assert status == "validated"
        assert (tmp_path / "VARIANTS" / name / "export" / f"{name}.mp4").exists()


def test_sharepoint_setup_upload_and_download_create_local_transfer_artifacts(tmp_path, capsys, monkeypatch) -> None:
    library_root = tmp_path / "video-library"
    monkeypatch.setenv("VIDEO_LIBRARY_ROOT", str(library_root))
    _bootstrap_workspace(tmp_path)
    export_dir = tmp_path / "VARIANTS" / "launch-cut" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    local_file = export_dir / "launch-cut.mp4"
    local_file.write_text("fake render", encoding="utf-8")

    assert main(["--workspace", str(tmp_path), "sharepoint", "setup"]) == 0
    assert "sharepoint setup completed" in capsys.readouterr().out

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "sharepoint",
                "upload",
                "--file",
                str(local_file),
                "--variant",
                "launch-cut",
            ]
        )
        == 0
    )
    assert "sharepoint upload completed" in capsys.readouterr().out

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "sharepoint",
                "download",
                "--variant",
                "launch-cut",
            ]
        )
        == 0
    )
    assert "sharepoint download completed" in capsys.readouterr().out

    assert (tmp_path / "sharepoint" / "setup.json").exists()
    assert (
        tmp_path
        / "sharepoint"
        / "library"
        / "Shared Documents"
        / "Variants"
        / "launch-cut"
        / "launch-cut.mp4"
    ).exists()
    assert (library_root / "raw" / "launch-cut" / "launch-cut.mp4").exists()


def test_competitor_and_perf_reports_are_written_and_loaded(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    _approve_ingested_clip(tmp_path, "hook-angle.mp4")
    _approve_ingested_clip(tmp_path, "body-offer.mp4")
    perf_csv = tmp_path / "inbox" / "perf" / "daily.csv"
    perf_csv.write_text(
        "variant,spend,clicks\nlaunch-cut,10.5,4\nlaunch-cut,5.0,2\nbackup-cut,2.5,1\n",
        encoding="utf-8",
    )

    assert main(["--workspace", str(tmp_path), "competitor", "analyze"]) == 0
    assert "competitor analyze completed" in capsys.readouterr().out
    assert main(["--workspace", str(tmp_path), "competitor", "report"]) == 0
    assert "competitor report loaded" in capsys.readouterr().out

    competitor_report = json.loads((tmp_path / "reports" / "competitor.json").read_text(encoding="utf-8"))
    assert competitor_report["asset_count"] >= 2
    assert competitor_report["approved_asset_count"] >= 2

    assert main(["--workspace", str(tmp_path), "perf", "ingest"]) == 0
    assert "perf ingest completed" in capsys.readouterr().out
    assert main(["--workspace", str(tmp_path), "perf", "report"]) == 0
    assert "perf report loaded" in capsys.readouterr().out

    perf_report = json.loads((tmp_path / "reports" / "perf.json").read_text(encoding="utf-8"))
    assert perf_report["csv_count"] == 1
    assert perf_report["row_count"] == 3
    assert perf_report["totals"]["spend"] == 18.0


def test_notify_and_voiceover_write_deterministic_outputs(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "notify",
                "progress",
                "--message",
                "phase-5-ready",
                "--dry-run",
            ]
        )
        == 0
    )
    assert "notify progress planned" in capsys.readouterr().out
    assert not (tmp_path / "logs" / "notify.log").exists()

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "notify",
                "render-done",
                "--variant",
                "launch-cut",
            ]
        )
        == 0
    )
    assert "notify render-done completed" in capsys.readouterr().out
    notify_log = tmp_path / "logs" / "notify.log"
    assert notify_log.exists()
    assert "launch-cut" in notify_log.read_text(encoding="utf-8")

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "voiceover",
                "generate",
                "--script",
                "Buy now and save.",
            ]
        )
        == 0
    )
    assert "voiceover generate completed" in capsys.readouterr().out

    manifest_files = sorted((tmp_path / "voiceover").glob("*.json"))
    audio_files = sorted((tmp_path / "voiceover").glob("*.mp3"))
    transcript_files = sorted((tmp_path / "voiceover").glob("*.txt"))
    assert manifest_files
    assert audio_files
    assert transcript_files
