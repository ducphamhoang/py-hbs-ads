from __future__ import annotations

import json
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


def test_legacy_style_variant_config_paths_work_end_to_end(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    hook_path = tmp_path / "_HOOKS" / "hook-question.mp4"
    body_path = tmp_path / "_ASSETS" / "gameplay" / "trimmed" / "body-offer.mp4"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text("hook media", encoding="utf-8")
    body_path.write_text("body media", encoding="utf-8")

    config_dir = tmp_path / "generated_variants"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "v204+v215.json"
    config_path.write_text(
        json.dumps(
            {
                "variant": "MixV204-V215_1080x1920",
                "clips": [
                    {"clip": "_HOOKS/hook-question.mp4"},
                    {"clip": "_ASSETS/gameplay/trimmed/body-offer.mp4"},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "variants",
                "assemble",
                "--config",
                "generated_variants/v204+v215.json",
            ]
        )
        == 0
    )
    assert "variants assemble completed" in capsys.readouterr().out

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "variants",
                "export",
                "--variant",
                "MixV204-V215_1080x1920",
            ]
        )
        == 0
    )
    assert "variants export completed" in capsys.readouterr().out

    assert (
        main(
            [
                "--workspace",
                str(tmp_path),
                "variants",
                "validate",
                "--platform",
                "tiktok",
            ]
        )
        == 0
    )
    assert "variants validate completed" in capsys.readouterr().out
    assert (
        tmp_path
        / "VARIANTS"
        / "MixV204-V215_1080x1920"
        / "export"
        / "MixV204-V215_1080x1920.mp4"
    ).exists()


def test_legacy_style_reporting_paths_work_with_json_mode(tmp_path, capsys) -> None:
    _bootstrap_workspace(tmp_path)
    capsys.readouterr()
    perf_csv = tmp_path / "inbox" / "perf" / "legacy-daily.csv"
    perf_csv.write_text(
        "ad_name,spend,clicks\nlegacy-cut,12.5,8\nlegacy-cut,7.5,5\n",
        encoding="utf-8",
    )

    assert main(["--workspace", str(tmp_path), "--json", "perf", "ingest"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "perf ingest"
    assert payload["data"]["report_file"].endswith("reports/perf.json")
