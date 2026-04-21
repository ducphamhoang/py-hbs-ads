from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hbs_ads.features.market_research.models import (
    AdCandidate,
    CreativeAnalysisResult,
    InsightCandidate,
    ResearchBrief,
    ReviewDecision,
    SyncReport,
    VariantCluster,
    ConceptCluster,
)


MIGRATIONS: list[tuple[str, str]] = [
    (
        "mr_0001_initial",
        """
        CREATE TABLE IF NOT EXISTS mr_schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
    (
        "mr_0002_briefs_and_runs",
        """
        CREATE TABLE IF NOT EXISTS mr_research_brief (
            brief_id TEXT PRIMARY KEY,
            research_goal TEXT NOT NULL DEFAULT '',
            market_scope_json TEXT NOT NULL DEFAULT '{}',
            competitor_scope_json TEXT NOT NULL DEFAULT '{}',
            creative_scope_json TEXT NOT NULL DEFAULT '{}',
            analysis_focus_json TEXT NOT NULL DEFAULT '[]',
            sampling_strategy TEXT NOT NULL DEFAULT '',
            output_mode TEXT NOT NULL DEFAULT '',
            review_mode TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS mr_run (
            run_id TEXT PRIMARY KEY,
            brief_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            operator TEXT NOT NULL DEFAULT 'system',
            notes TEXT NOT NULL DEFAULT ''
        );
        """,
    ),
    (
        "mr_0003_candidates",
        """
        CREATE TABLE IF NOT EXISTS mr_ad_candidate (
            candidate_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            query_id TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            source_record_id TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            app_name TEXT NOT NULL DEFAULT '',
            publisher_name TEXT NOT NULL DEFAULT '',
            geo TEXT NOT NULL DEFAULT '',
            platform TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT NOT NULL DEFAULT '',
            asset_url TEXT NOT NULL DEFAULT '',
            thumbnail_url TEXT NOT NULL DEFAULT '',
            landing_url TEXT NOT NULL DEFAULT '',
            raw_payload_json TEXT NOT NULL DEFAULT '{}',
            normalized_status TEXT NOT NULL DEFAULT 'raw',
            dedupe_key TEXT NOT NULL DEFAULT ''
        );
        """,
    ),
    (
        "mr_0004_clusters",
        """
        CREATE TABLE IF NOT EXISTS mr_variant_cluster (
            variant_cluster_id TEXT PRIMARY KEY,
            cluster_label TEXT NOT NULL DEFAULT '',
            representative_asset_id TEXT NOT NULL DEFAULT '',
            member_asset_ids_json TEXT NOT NULL DEFAULT '[]',
            cluster_confidence REAL NOT NULL DEFAULT 1.0,
            clustering_method TEXT NOT NULL DEFAULT '',
            review_status TEXT NOT NULL DEFAULT 'provisional',
            review_notes TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS mr_concept_cluster (
            concept_cluster_id TEXT PRIMARY KEY,
            cluster_label TEXT NOT NULL DEFAULT '',
            representative_variant_cluster_id TEXT NOT NULL DEFAULT '',
            member_variant_cluster_ids_json TEXT NOT NULL DEFAULT '[]',
            concept_summary TEXT NOT NULL DEFAULT '',
            cluster_confidence REAL NOT NULL DEFAULT 0.7,
            review_status TEXT NOT NULL DEFAULT 'provisional',
            review_notes TEXT NOT NULL DEFAULT ''
        );
        """,
    ),
    (
        "mr_0005_analyses",
        """
        CREATE TABLE IF NOT EXISTS mr_creative_analysis (
            analysis_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            asset_id TEXT NOT NULL DEFAULT '',
            variant_cluster_id TEXT NOT NULL DEFAULT '',
            concept_cluster_id TEXT NOT NULL DEFAULT '',
            model_provider TEXT NOT NULL DEFAULT 'gemini',
            model_name TEXT NOT NULL DEFAULT '',
            schema_version TEXT NOT NULL DEFAULT '',
            observable_json TEXT NOT NULL DEFAULT '{}',
            taxonomy_tags_json TEXT NOT NULL DEFAULT '{}',
            interpretation_json TEXT NOT NULL DEFAULT '{}',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            quality_json TEXT NOT NULL DEFAULT '{}',
            analysis_status TEXT NOT NULL DEFAULT 'ok',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
    (
        "mr_0006_insights_and_reviews",
        """
        CREATE TABLE IF NOT EXISTS mr_insight_candidate (
            insight_candidate_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            insight_type TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            signal TEXT NOT NULL DEFAULT '',
            evidence_summary_json TEXT NOT NULL DEFAULT '{}',
            scope_json TEXT NOT NULL DEFAULT '{}',
            confidence TEXT NOT NULL DEFAULT 'medium',
            implication TEXT NOT NULL DEFAULT '',
            evidence_refs_json TEXT NOT NULL DEFAULT '[]',
            needs_human_review INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mr_review_decision (
            review_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            target_type TEXT NOT NULL DEFAULT '',
            target_id TEXT NOT NULL DEFAULT '',
            reviewer TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            updated_confidence TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mr_sync_report (
            run_id TEXT PRIMARY KEY,
            synced_candidates INTEGER NOT NULL DEFAULT 0,
            synced_assets INTEGER NOT NULL DEFAULT 0,
            synced_clusters INTEGER NOT NULL DEFAULT 0,
            synced_analyses INTEGER NOT NULL DEFAULT 0,
            synced_insights INTEGER NOT NULL DEFAULT 0,
            synced_reviews INTEGER NOT NULL DEFAULT 0,
            errors_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ),
]


class MarketResearchSQLiteDB:
    def __init__(self, path: Path) -> None:
        self.path = path

    def bootstrap(self) -> list[str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        applied: list[str] = []
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mr_schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            existing = {
                row[0]
                for row in conn.execute("SELECT version FROM mr_schema_migrations").fetchall()
            }
            for version, sql in MIGRATIONS:
                if version in existing:
                    continue
                conn.executescript(sql)
                conn.execute("INSERT INTO mr_schema_migrations(version) VALUES (?)", (version,))
                applied.append(version)
            conn.commit()
        return applied

    # ------------------------------------------------------------------ #
    # Write helpers                                                        #
    # ------------------------------------------------------------------ #

    def upsert_brief(self, brief: ResearchBrief) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_research_brief
                    (brief_id, research_goal, market_scope_json, competitor_scope_json,
                     creative_scope_json, analysis_focus_json, sampling_strategy,
                     output_mode, review_mode, created_at, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(brief_id) DO UPDATE SET
                    research_goal = excluded.research_goal,
                    market_scope_json = excluded.market_scope_json,
                    competitor_scope_json = excluded.competitor_scope_json,
                    creative_scope_json = excluded.creative_scope_json,
                    analysis_focus_json = excluded.analysis_focus_json,
                    sampling_strategy = excluded.sampling_strategy,
                    output_mode = excluded.output_mode,
                    review_mode = excluded.review_mode
                """,
                (
                    brief.brief_id,
                    brief.research_goal,
                    json.dumps(brief.market_scope),
                    json.dumps(brief.competitor_scope),
                    json.dumps(brief.creative_scope),
                    json.dumps(brief.analysis_focus),
                    brief.sampling_strategy,
                    brief.output_mode,
                    brief.review_mode,
                    brief.created_at,
                    brief.created_by,
                ),
            )
            conn.commit()

    def upsert_run(
        self,
        *,
        run_id: str,
        brief_id: str,
        status: str,
        operator: str,
        finished_at: str = "",
        notes: str = "",
    ) -> None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_run
                    (run_id, brief_id, status, operator, finished_at, notes)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    brief_id = excluded.brief_id,
                    status = excluded.status,
                    operator = excluded.operator,
                    finished_at = excluded.finished_at,
                    notes = excluded.notes
                """,
                (run_id, brief_id, status, operator, finished_at or None, notes),
            )
            conn.commit()

    def upsert_candidate(self, candidate: AdCandidate) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_ad_candidate
                    (candidate_id, run_id, query_id, source, source_record_id,
                     source_url, app_name, publisher_name, geo, platform,
                     first_seen_at, last_seen_at, asset_url, thumbnail_url,
                     landing_url, raw_payload_json, normalized_status, dedupe_key)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    normalized_status = excluded.normalized_status,
                    dedupe_key = excluded.dedupe_key
                """,
                (
                    candidate.candidate_id, candidate.run_id, candidate.query_id,
                    candidate.source, candidate.source_record_id, candidate.source_url,
                    candidate.app_name, candidate.publisher_name, candidate.geo, candidate.platform,
                    candidate.first_seen_at, candidate.last_seen_at, candidate.asset_url,
                    candidate.thumbnail_url, candidate.landing_url,
                    json.dumps(candidate.raw_payload), candidate.normalized_status, candidate.dedupe_key,
                ),
            )
            conn.commit()

    def upsert_variant_cluster(self, vc: VariantCluster) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_variant_cluster
                    (variant_cluster_id, cluster_label, representative_asset_id,
                     member_asset_ids_json, cluster_confidence, clustering_method,
                     review_status, review_notes)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(variant_cluster_id) DO UPDATE SET
                    review_status = excluded.review_status,
                    review_notes = excluded.review_notes
                """,
                (
                    vc.variant_cluster_id, vc.cluster_label, vc.representative_asset_id,
                    json.dumps(vc.member_asset_ids), vc.cluster_confidence,
                    vc.clustering_method, vc.review_status, vc.review_notes,
                ),
            )
            conn.commit()

    def upsert_concept_cluster(self, cc: ConceptCluster) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_concept_cluster
                    (concept_cluster_id, cluster_label, representative_variant_cluster_id,
                     member_variant_cluster_ids_json, concept_summary, cluster_confidence,
                     review_status, review_notes)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(concept_cluster_id) DO UPDATE SET
                    review_status = excluded.review_status
                """,
                (
                    cc.concept_cluster_id, cc.cluster_label, cc.representative_variant_cluster_id,
                    json.dumps(cc.member_variant_cluster_ids), cc.concept_summary,
                    cc.cluster_confidence, cc.review_status, cc.review_notes,
                ),
            )
            conn.commit()

    def upsert_analysis(self, analysis: CreativeAnalysisResult) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_creative_analysis
                    (analysis_id, run_id, asset_id, variant_cluster_id, concept_cluster_id,
                     model_provider, model_name, schema_version,
                     observable_json, taxonomy_tags_json, interpretation_json,
                     evidence_json, quality_json, analysis_status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(analysis_id) DO UPDATE SET
                    analysis_status = excluded.analysis_status,
                    quality_json = excluded.quality_json
                """,
                (
                    analysis.analysis_id, analysis.run_id, analysis.asset_id,
                    analysis.variant_cluster_id, analysis.concept_cluster_id,
                    analysis.model_provider, analysis.model_name, analysis.schema_version,
                    json.dumps(analysis.observable), json.dumps(analysis.taxonomy_tags),
                    json.dumps(analysis.interpretation), json.dumps(analysis.evidence),
                    json.dumps(analysis.quality), analysis.analysis_status, analysis.created_at,
                ),
            )
            conn.commit()

    def upsert_insight(self, insight: InsightCandidate) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_insight_candidate
                    (insight_candidate_id, run_id, insight_type, title, signal,
                     evidence_summary_json, scope_json, confidence, implication,
                     evidence_refs_json, needs_human_review, status, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(insight_candidate_id) DO UPDATE SET
                    status = excluded.status,
                    confidence = excluded.confidence,
                    needs_human_review = excluded.needs_human_review
                """,
                (
                    insight.insight_candidate_id, insight.run_id, insight.insight_type,
                    insight.title, insight.signal, json.dumps(insight.evidence_summary),
                    json.dumps(insight.scope), insight.confidence, insight.implication,
                    json.dumps(insight.evidence_refs), int(insight.needs_human_review),
                    insight.status, insight.created_at,
                ),
            )
            conn.commit()

    def upsert_review(self, review: ReviewDecision) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_review_decision
                    (review_id, run_id, target_type, target_id, reviewer,
                     decision, rationale, updated_confidence, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(review_id) DO NOTHING
                """,
                (
                    review.review_id, review.run_id, review.target_type, review.target_id,
                    review.reviewer, review.decision, review.rationale,
                    review.updated_confidence, review.created_at,
                ),
            )
            conn.commit()

    def upsert_sync_report(self, report: SyncReport) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO mr_sync_report
                    (run_id, synced_candidates, synced_assets, synced_clusters,
                     synced_analyses, synced_insights, synced_reviews, errors_json, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    synced_candidates = excluded.synced_candidates,
                    synced_analyses = excluded.synced_analyses,
                    synced_insights = excluded.synced_insights
                """,
                (
                    report.run_id, report.synced_candidates, report.synced_assets,
                    report.synced_clusters, report.synced_analyses, report.synced_insights,
                    report.synced_reviews, json.dumps(report.errors), report.created_at,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Batch sync — called by MarketResearchService                        #
    # ------------------------------------------------------------------ #

    def sync_run(
        self,
        run_id: str,
        brief_id: str,
        operator: str,
        status: str,
        finished_at: str,
        candidates: list[AdCandidate],
        cluster_result: dict[str, Any],
        analyses: list[CreativeAnalysisResult],
        insights: list[InsightCandidate],
        reviews: list[ReviewDecision],
    ) -> None:
        self.bootstrap()
        self.upsert_run(
            run_id=run_id,
            brief_id=brief_id,
            status=status,
            operator=operator,
            finished_at=finished_at,
        )
        for c in candidates:
            self.upsert_candidate(c)
        for vc in cluster_result.get("variant_clusters", []):
            self.upsert_variant_cluster(vc)
        for cc in cluster_result.get("concept_clusters", []):
            self.upsert_concept_cluster(cc)
        for a in analyses:
            self.upsert_analysis(a)
        for i in insights:
            self.upsert_insight(i)
        for r in reviews:
            self.upsert_review(r)

    # ------------------------------------------------------------------ #
    # Read helpers                                                         #
    # ------------------------------------------------------------------ #

    def list_candidates(self, run_id: str) -> list[dict[str, Any]]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT candidate_id, source, app_name, platform, geo, dedupe_key "
                "FROM mr_ad_candidate WHERE run_id = ? ORDER BY candidate_id",
                (run_id,),
            ).fetchall()
        return [
            {"candidate_id": r[0], "source": r[1], "app_name": r[2],
             "platform": r[3], "geo": r[4], "dedupe_key": r[5]}
            for r in rows
        ]

    def list_insights(self, run_id: str) -> list[dict[str, Any]]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT insight_candidate_id, title, confidence, status "
                "FROM mr_insight_candidate WHERE run_id = ? ORDER BY insight_candidate_id",
                (run_id,),
            ).fetchall()
        return [
            {"insight_candidate_id": r[0], "title": r[1], "confidence": r[2], "status": r[3]}
            for r in rows
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT run_id, brief_id, status, created_at, finished_at, operator, notes "
                "FROM mr_run WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "brief_id": row[1],
            "status": row[2],
            "created_at": row[3],
            "finished_at": row[4] or "",
            "operator": row[5],
            "notes": row[6],
        }

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT run_id, brief_id, status, created_at, finished_at, operator "
                "FROM mr_run ORDER BY COALESCE(finished_at, created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "run_id": row[0],
                "brief_id": row[1],
                "status": row[2],
                "created_at": row[3],
                "finished_at": row[4] or "",
                "operator": row[5],
            }
            for row in rows
        ]

    def load_analyses(
        self,
        run_id: str,
        *,
        analysis_status: str = "",
    ) -> list[CreativeAnalysisResult]:
        self.bootstrap()
        sql = (
            "SELECT analysis_id, run_id, asset_id, variant_cluster_id, concept_cluster_id, "
            "model_provider, model_name, schema_version, observable_json, taxonomy_tags_json, "
            "interpretation_json, evidence_json, quality_json, analysis_status, created_at "
            "FROM mr_creative_analysis WHERE run_id = ?"
        )
        params: list[Any] = [run_id]
        if analysis_status:
            sql += " AND analysis_status = ?"
            params.append(analysis_status)
        sql += " ORDER BY analysis_id"

        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        return [
            CreativeAnalysisResult(
                analysis_id=row[0],
                run_id=row[1],
                asset_id=row[2],
                variant_cluster_id=row[3],
                concept_cluster_id=row[4],
                model_provider=row[5],
                model_name=row[6],
                schema_version=row[7],
                observable=json.loads(row[8]),
                taxonomy_tags=json.loads(row[9]),
                interpretation=json.loads(row[10]),
                evidence=json.loads(row[11]),
                quality=json.loads(row[12]),
                analysis_status=row[13],
                created_at=row[14],
            )
            for row in rows
        ]

    def load_insight_candidates(self, run_id: str) -> list[InsightCandidate]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT insight_candidate_id, run_id, insight_type, title, signal, evidence_summary_json, "
                "scope_json, confidence, implication, evidence_refs_json, needs_human_review, status, created_at "
                "FROM mr_insight_candidate WHERE run_id = ? ORDER BY insight_candidate_id",
                (run_id,),
            ).fetchall()

        return [
            InsightCandidate(
                insight_candidate_id=row[0],
                run_id=row[1],
                insight_type=row[2],
                title=row[3],
                signal=row[4],
                evidence_summary=json.loads(row[5]),
                scope=json.loads(row[6]),
                confidence=row[7],
                implication=row[8],
                evidence_refs=json.loads(row[9]),
                needs_human_review=bool(row[10]),
                status=row[11],
                created_at=row[12],
            )
            for row in rows
        ]

    def load_reviews(self, run_id: str) -> list[ReviewDecision]:
        self.bootstrap()
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT review_id, run_id, target_type, target_id, reviewer, decision, rationale, updated_confidence, created_at "
                "FROM mr_review_decision WHERE run_id = ? ORDER BY review_id",
                (run_id,),
            ).fetchall()

        return [
            ReviewDecision(
                review_id=row[0],
                run_id=row[1],
                target_type=row[2],
                target_id=row[3],
                reviewer=row[4],
                decision=row[5],
                rationale=row[6],
                updated_confidence=row[7],
                created_at=row[8],
            )
            for row in rows
        ]
