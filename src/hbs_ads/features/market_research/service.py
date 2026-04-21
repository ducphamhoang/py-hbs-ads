from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hbs_ads.features.market_research.clustering import run_clustering
from hbs_ads.features.market_research.enrichment import enrich_run
from hbs_ads.features.market_research.models import (
    AdCandidate,
    ConceptCluster,
    CreativeAnalysisResult,
    InsightCandidate,
    MarketQueryRecord,
    MarketResearchRunRequest,
    ResearchBrief,
    ReviewDecision,
    SyncReport,
    VariantCluster,
)
from hbs_ads.features.market_research.normalization import normalize_candidates
from hbs_ads.features.market_research.review import batch_approve
from hbs_ads.features.market_research.synthesis import synthesize_insights
from hbs_ads.features.market_research.validators import (
    validate_brief,
    validate_insight_candidate,
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _artifact_dataclass_list(path: Path, cls: Any) -> list[Any]:
    if not path.exists():
        return []
    payload = _read_json(path)
    return [cls(**item) for item in payload]


class MarketResearchService:
    def __init__(
        self,
        workspace_path: Path,
        *,
        gemini_analyzer: Any | None = None,
        db: Any | None = None,
    ) -> None:
        self.workspace = workspace_path
        self.artifact_root = workspace_path / "logs" / "market-research"
        self.gemini_analyzer = gemini_analyzer
        self.db = db

    # ------------------------------------------------------------------ #
    # Stage: brief                                                         #
    # ------------------------------------------------------------------ #

    def store_brief(self, brief: ResearchBrief) -> Path:
        errors = validate_brief(brief)
        if errors:
            raise ValueError(f"Invalid research brief: {errors}")
        path = self.artifact_root / "brief.json"
        _write_json(path, asdict(brief))
        if self.db is not None and hasattr(self.db, "upsert_brief"):
            self.db.upsert_brief(brief)
        return path

    def load_brief(self) -> ResearchBrief:
        path = self.artifact_root / "brief.json"
        data = _read_json(path)
        return ResearchBrief(**{k: v for k, v in data.items() if k in ResearchBrief.__dataclass_fields__})

    # ------------------------------------------------------------------ #
    # Stage: collect                                                       #
    # ------------------------------------------------------------------ #

    def collect_from_manifest(self, run_id: str, manifest_path: Path) -> list[AdCandidate]:
        raw_data = _read_json(manifest_path)
        records: list[dict[str, Any]] = raw_data if isinstance(raw_data, list) else raw_data.get("candidates", [])
        query_id = f"query_{run_id}_manifest"
        candidates = normalize_candidates(run_id, query_id, records)
        out = self.artifact_root / "collect" / "candidates.raw.json"
        _write_json(out, [asdict(c) for c in candidates])
        manifest_out = self.artifact_root / "collect" / "assets-manifest.json"
        _write_json(manifest_out, {"run_id": run_id, "source": str(manifest_path), "count": len(candidates)})
        return candidates

    # ------------------------------------------------------------------ #
    # Stage: normalize                                                     #
    # ------------------------------------------------------------------ #

    def normalize(self, candidates: list[AdCandidate]) -> list[AdCandidate]:
        out = self.artifact_root / "normalize" / "candidates.normalized.json"
        _write_json(out, [asdict(c) for c in candidates])
        return candidates

    # ------------------------------------------------------------------ #
    # Stage: cluster                                                       #
    # ------------------------------------------------------------------ #

    def cluster(self, candidates: list[AdCandidate]) -> dict[str, Any]:
        result = run_clustering(candidates)
        _write_json(
            self.artifact_root / "cluster" / "asset-dedupe.json",
            {cid: aid for cid, aid in result["dedupe_map"].items()},
        )
        _write_json(
            self.artifact_root / "cluster" / "variant-clusters.json",
            [asdict(vc) for vc in result["variant_clusters"]],
        )
        _write_json(
            self.artifact_root / "cluster" / "concept-clusters.json",
            [asdict(cc) for cc in result["concept_clusters"]],
        )
        
        # Run representative selection
        from hbs_ads.features.market_research.selection import run_representative_selection
        selection_result = run_representative_selection(result, [asdict(c) for c in candidates])
        _write_json(
            self.artifact_root / "cluster" / "representative-selection.json",
            {
                "selected_assets": selection_result["selected_assets"],
                "variant_cluster_decisions": [
                    {
                        "cluster_id": d.cluster_id,
                        "cluster_type": d.cluster_type,
                        "selected_asset_ids": d.selected_asset_ids,
                        "selection_reason": d.selection_reason,
                        "selection_confidence": d.selection_confidence,
                        "fallback_used": d.fallback_used,
                        "excluded_asset_ids": d.excluded_asset_ids,
                        "notes": d.notes,
                    }
                    for d in selection_result["variant_cluster_decisions"]
                ],
                "concept_cluster_decisions": [
                    {
                        "cluster_id": d.cluster_id,
                        "cluster_type": d.cluster_type,
                        "selected_asset_ids": d.selected_asset_ids,
                        "selection_reason": d.selection_reason,
                        "selection_confidence": d.selection_confidence,
                        "split_dimensions": d.split_dimensions,
                        "fallback_used": d.fallback_used,
                        "notes": d.notes,
                    }
                    for d in selection_result["concept_cluster_decisions"]
                ],
            },
        )
        result["selection"] = selection_result
        return result

    # ------------------------------------------------------------------ #
    # Stage: analyze                                                       #
    # ------------------------------------------------------------------ #

    def analyze(
        self,
        run_id: str,
        cluster_result: dict[str, Any],
    ) -> list[CreativeAnalysisResult]:
        analyses: list[CreativeAnalysisResult] = []
        failures: list[dict[str, Any]] = []

        # Use representative selection if available, otherwise fall back to variant cluster representatives
        selection = cluster_result.get("selection")
        if selection:
            selected_asset_ids = set(selection.get("selected_assets", []))
        else:
            # Fallback: use representative_asset_id from each variant cluster
            variant_clusters = cluster_result.get("variant_clusters", [])
            selected_asset_ids = {vc.representative_asset_id for vc in variant_clusters}

        assets = {a.asset_id: a for a in cluster_result.get("assets", [])}
        asset_to_variant_cluster_id: dict[str, str] = {}
        for variant_cluster in cluster_result.get("variant_clusters", []):
            for member_asset_id in variant_cluster.member_asset_ids:
                asset_to_variant_cluster_id[member_asset_id] = variant_cluster.variant_cluster_id

        out_dir = self.artifact_root / "analyze"
        out_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = out_dir / "creative-analysis.jsonl"
        failure_file = out_dir / "failures.json"

        with analysis_file.open("w", encoding="utf-8") as fh:
            for asset_id in selected_asset_ids:
                asset = assets.get(asset_id)
                if asset is None:
                    continue
                if self.gemini_analyzer and asset.canonical_path:
                    try:
                        result = self.gemini_analyzer.analyze_asset(
                            asset_path=Path(asset.canonical_path),
                            run_id=run_id,
                            asset_id=asset.asset_id,
                            variant_cluster_id=asset_to_variant_cluster_id.get(asset.asset_id, ""),
                        )
                        analyses.append(result)
                        fh.write(json.dumps(asdict(result), default=str) + "\n")
                    except Exception as exc:
                        failures.append({
                            "asset_id": asset.asset_id,
                            "error": str(exc),
                        })
                else:
                    stub = CreativeAnalysisResult(
                        analysis_id=f"analysis_{asset.asset_id}",
                        run_id=run_id,
                        asset_id=asset.asset_id,
                        variant_cluster_id=asset_to_variant_cluster_id.get(asset.asset_id, ""),
                        analysis_status="skipped_no_analyzer",
                        created_at=_now_iso(),
                    )
                    analyses.append(stub)
                    fh.write(json.dumps(asdict(stub), default=str) + "\n")

        _write_json(failure_file, failures)
        return analyses

    # ------------------------------------------------------------------ #
    # Stage: enrich                                                        #
    # ------------------------------------------------------------------ #

    def enrich(
        self,
        candidates: list[AdCandidate],
        cluster_result: dict[str, Any],
    ) -> dict[str, Any]:
        enrichment = enrich_run(
            candidates,
            cluster_result.get("variant_clusters", []),
            cluster_result.get("concept_clusters", []),
        )
        _write_json(self.artifact_root / "enrich" / "context.json", enrichment)
        _write_json(
            self.artifact_root / "enrich" / "cluster-metrics.json",
            enrichment.get("cluster_metrics", {}),
        )
        return enrichment

    # ------------------------------------------------------------------ #
    # Stage: synthesize                                                    #
    # ------------------------------------------------------------------ #

    def synthesize(
        self,
        run_id: str,
        analyses: list[CreativeAnalysisResult],
        brief: ResearchBrief,
        cluster_result: dict[str, Any],
    ) -> list[InsightCandidate]:
        valid_analyses = [a for a in analyses if a.analysis_status == "ok"]
        insights = synthesize_insights(
            valid_analyses,
            brief,
            run_id,
            cluster_result.get("variant_clusters"),
            cluster_result.get("concept_clusters"),
        )
        out = self.artifact_root / "synthesize" / "insight-candidates.json"
        _write_json(out, [asdict(i) for i in insights])
        return insights

    # ------------------------------------------------------------------ #
    # Readback / reuse helpers                                            #
    # ------------------------------------------------------------------ #

    def load_run_state(self) -> dict[str, Any]:
        return _read_json(self.artifact_root / "run-state.json")

    def load_failures(self) -> list[dict[str, Any]]:
        return _read_json(self.artifact_root / "analyze" / "failures.json")

    def load_analyses(
        self,
        *,
        run_id: str = "",
        from_db: bool = False,
        analysis_status: str = "",
    ) -> list[CreativeAnalysisResult]:
        if from_db and self.db is not None and hasattr(self.db, "load_analyses"):
            target_run_id = run_id or self.load_run_state().get("run_id", "")
            return self.db.load_analyses(target_run_id, analysis_status=analysis_status)

        analyses = [
            CreativeAnalysisResult(**row)
            for row in _read_jsonl(self.artifact_root / "analyze" / "creative-analysis.jsonl")
        ]
        if run_id:
            analyses = [analysis for analysis in analyses if analysis.run_id == run_id]
        if analysis_status:
            analyses = [analysis for analysis in analyses if analysis.analysis_status == analysis_status]
        return analyses

    def load_insights(
        self,
        *,
        run_id: str = "",
        from_db: bool = False,
    ) -> list[InsightCandidate]:
        if from_db and self.db is not None and hasattr(self.db, "load_insight_candidates"):
            target_run_id = run_id or self.load_run_state().get("run_id", "")
            return self.db.load_insight_candidates(target_run_id)

        insights = _artifact_dataclass_list(
            self.artifact_root / "synthesize" / "insight-candidates.json",
            InsightCandidate,
        )
        if run_id:
            insights = [insight for insight in insights if insight.run_id == run_id]
        return insights

    def load_reviews(
        self,
        *,
        run_id: str = "",
        from_db: bool = False,
    ) -> list[ReviewDecision]:
        if from_db and self.db is not None and hasattr(self.db, "load_reviews"):
            target_run_id = run_id or self.load_run_state().get("run_id", "")
            return self.db.load_reviews(target_run_id)

        reviews = _artifact_dataclass_list(
            self.artifact_root / "review" / "review-decisions.json",
            ReviewDecision,
        )
        if run_id:
            reviews = [review for review in reviews if review.run_id == run_id]
        return reviews

    def debug_asset(
        self,
        *,
        asset_path: Path,
        run_id: str,
        asset_id: str,
        variant_cluster_id: str = "",
        analysis_focus: list[str] | None = None,
    ) -> CreativeAnalysisResult:
        if self.gemini_analyzer is None:
            raise ValueError("debug_asset requires a configured gemini_analyzer")

        result = self.gemini_analyzer.analyze_asset(
            asset_path=asset_path,
            run_id=run_id,
            asset_id=asset_id,
            variant_cluster_id=variant_cluster_id,
            analysis_focus=analysis_focus,
        )
        _write_json(self.artifact_root / "debug" / f"{asset_id}.debug-analysis.json", asdict(result))
        return result

    def re_synthesize_from_saved_analyses(
        self,
        brief: ResearchBrief,
        *,
        source_run_id: str = "",
        operator: str = "system",
    ) -> dict[str, Any]:
        errors = validate_brief(brief)
        if errors:
            raise ValueError(f"Invalid research brief: {errors}")

        active_run_id = source_run_id or self.load_run_state().get("run_id", "")
        if not active_run_id:
            raise ValueError("source_run_id is required when no run-state exists")

        analyses = self.load_analyses(
            run_id=active_run_id,
            from_db=self.db is not None,
            analysis_status="ok",
        )
        if not analyses:
            raise ValueError(f"No successful analyses available for run {active_run_id}")

        variant_clusters = _artifact_dataclass_list(
            self.artifact_root / "cluster" / "variant-clusters.json",
            VariantCluster,
        )
        concept_clusters = _artifact_dataclass_list(
            self.artifact_root / "cluster" / "concept-clusters.json",
            ConceptCluster,
        )

        new_run_id = f"resynth_{brief.brief_id}_{uuid.uuid4().hex[:8]}"
        insights = synthesize_insights(analyses, brief, new_run_id, variant_clusters, concept_clusters)
        invalid = {
            insight.insight_candidate_id: validate_insight_candidate(insight)
            for insight in insights
            if validate_insight_candidate(insight)
        }
        if invalid:
            raise ValueError(f"Invalid synthesized insights: {invalid}")

        output_artifact = self.artifact_root / "synthesize" / f"insight-candidates.{new_run_id}.json"
        report = {
            "run_id": new_run_id,
            "status": "completed",
            "source_run_id": active_run_id,
            "brief_id": brief.brief_id,
            "insight_count": len(insights),
            "review_status": "draft_only",
            "requires_human_review": any(insight.needs_human_review for insight in insights),
            "output_artifact": str(output_artifact),
            "created_at": _now_iso(),
        }
        _write_json(output_artifact, [asdict(insight) for insight in insights])
        _write_json(
            self.artifact_root / "synthesize" / f"re-synthesis-report.{new_run_id}.json",
            report,
        )

        if self.db is not None:
            if hasattr(self.db, "upsert_brief"):
                self.db.upsert_brief(brief)
            if hasattr(self.db, "upsert_run"):
                self.db.upsert_run(
                    run_id=new_run_id,
                    brief_id=brief.brief_id,
                    status="resynthesized",
                    operator=operator,
                    finished_at=report["created_at"],
                    notes=f"source_run_id={active_run_id}",
                )
            if hasattr(self.db, "upsert_insight"):
                for insight in insights:
                    self.db.upsert_insight(insight)

        return report

    # ------------------------------------------------------------------ #
    # Stage: review                                                        #
    # ------------------------------------------------------------------ #

    def review(
        self,
        insights: list[InsightCandidate],
        *,
        reviewer: str = "system",
        auto_approve: bool = False,
    ) -> tuple[list[InsightCandidate], list[ReviewDecision]]:
        if auto_approve:
            updated, reviews = batch_approve(insights, reviewer=reviewer, rationale="auto_approve")
        else:
            updated, reviews = insights, []

        _write_json(
            self.artifact_root / "review" / "review-decisions.json",
            [asdict(r) for r in reviews],
        )
        return updated, reviews

    # ------------------------------------------------------------------ #
    # Stage: sync                                                          #
    # ------------------------------------------------------------------ #

    def sync(
        self,
        candidates: list[AdCandidate],
        cluster_result: dict[str, Any],
        analyses: list[CreativeAnalysisResult],
        insights: list[InsightCandidate],
        reviews: list[ReviewDecision],
        run_id: str,
        *,
        brief_id: str,
        operator: str,
    ) -> SyncReport:
        report = SyncReport(
            run_id=run_id,
            synced_candidates=len(candidates),
            synced_assets=len(cluster_result.get("assets", [])),
            synced_clusters=(
                len(cluster_result.get("variant_clusters", []))
                + len(cluster_result.get("concept_clusters", []))
            ),
            synced_analyses=len(analyses),
            synced_insights=len(insights),
            synced_reviews=len(reviews),
            created_at=_now_iso(),
        )

        if self.db is not None:
            self.db.sync_run(
                run_id=run_id,
                brief_id=brief_id,
                operator=operator,
                status="completed",
                finished_at=report.created_at,
                candidates=candidates,
                cluster_result=cluster_result,
                analyses=analyses,
                insights=insights,
                reviews=reviews,
            )
            if hasattr(self.db, "upsert_sync_report"):
                self.db.upsert_sync_report(report)

        _write_json(self.artifact_root / "sync" / "sync-report.json", asdict(report))
        return report

    # ------------------------------------------------------------------ #
    # Full run                                                             #
    # ------------------------------------------------------------------ #

    def run(self, request: MarketResearchRunRequest) -> dict[str, Any]:
        import uuid
        run_id = f"run_{request.brief.brief_id}_{uuid.uuid4().hex[:8]}"
        brief = request.brief

        brief_path = self.store_brief(brief)

        if request.manifest_path:
            candidates = self.collect_from_manifest(run_id, Path(request.manifest_path))
        else:
            candidates = []

        candidates = self.normalize(candidates)
        cluster_result = self.cluster(candidates)
        analyses = self.analyze(run_id, cluster_result)
        enrichment = self.enrich(candidates, cluster_result)
        insights = self.synthesize(run_id, analyses, brief, cluster_result)
        updated_insights, reviews = self.review(
            insights,
            reviewer=request.operator,
            auto_approve=(brief.review_mode == "auto"),
        )
        report = self.sync(
            candidates,
            cluster_result,
            analyses,
            updated_insights,
            reviews,
            run_id,
            brief_id=brief.brief_id,
            operator=request.operator,
        )

        run_state = {
            "run_id": run_id,
            "brief_id": brief.brief_id,
            "stages_completed": ["brief", "collect", "normalize", "cluster", "analyze", "enrich", "synthesize", "review", "sync"],
            "candidate_count": len(candidates),
            "insight_count": len(insights),
            "review_status": "approved" if reviews else "draft_only",
            "requires_human_review": any(insight.needs_human_review for insight in updated_insights),
            "created_at": _now_iso(),
        }
        _write_json(self.artifact_root / "run-state.json", run_state)

        return {
            "run_id": run_id,
            "status": "completed",
            "review_status": run_state["review_status"],
            "requires_human_review": run_state["requires_human_review"],
            "sync_report": asdict(report),
            "insight_count": len(insights),
        }
