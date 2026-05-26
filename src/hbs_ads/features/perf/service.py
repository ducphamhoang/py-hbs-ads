from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager


@dataclass(slots=True)
class PerfIngestRequest:
    workspace_root: Path
    dry_run: bool = False


@dataclass(slots=True)
class PerfReportRequest:
    workspace_root: Path


class PerfService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
    ) -> None:
        self.settings = settings
        self.workspace = workspace

    def ingest(self, request: PerfIngestRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        csv_files = sorted(layout.perf_inbox_dir.glob("*.csv"))
        rows: list[dict[str, str]] = []
        totals: dict[str, float] = {}
        by_variant: dict[str, dict[str, float | int]] = {}
        for csv_file in csv_files:
            with csv_file.open(newline="", encoding="utf-8", errors="replace") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append(row)
                    metrics = self._extract_numeric_metrics(row)
                    variant = self._detect_variant(row)
                    summary = by_variant.setdefault(variant, {"rows": 0})
                    summary["rows"] = int(summary["rows"]) + 1
                    for key, value in metrics.items():
                        totals[key] = totals.get(key, 0.0) + value
                        summary[key] = float(summary.get(key, 0.0)) + value

        report = {
            "workspace_root": str(layout.root),
            "csv_count": len(csv_files),
            "row_count": len(rows),
            "totals": totals,
            "variants": [
                {"variant": name, **summary}
                for name, summary in sorted(by_variant.items())
            ],
        }
        report_path = layout.reports_dir / "perf.json"
        if not request.dry_run:
            try:
                layout.reports_dir.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            except OSError as e:
                raise AppError(f"Failed to write {report_path}: {e}") from e
        return CommandResult(
            status="planned" if request.dry_run else "ok",
            message=f"perf ingest {'planned' if request.dry_run else 'completed'}",
            data={
                "report_file": str(report_path),
                "csv_count": report["csv_count"],
                "row_count": report["row_count"],
                "dry_run": request.dry_run,
            },
        )

    def report(self, request: PerfReportRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        report_path = layout.reports_dir / "perf.json"
        if not report_path.exists():
            raise AppError("perf report not found; run perf ingest first")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise AppError(f"Invalid JSON in {report_path}: {e}") from e
        return CommandResult(
            status="ok",
            message=f"perf report loaded from {report_path}",
            data=report,
        )

    def _extract_numeric_metrics(self, row: dict[str, str]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        for key, value in row.items():
            if value is None:
                continue
            try:
                metrics[key.strip().lower()] = float(value)
            except ValueError:
                continue
        return metrics

    def _detect_variant(self, row: dict[str, str]) -> str:
        for key in ("variant", "creative", "asset", "ad_name", "name"):
            value = row.get(key)
            if value:
                return value.strip()
        return "unknown"
