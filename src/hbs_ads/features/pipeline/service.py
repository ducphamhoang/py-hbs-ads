from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.features.hooks.service import AssembleHookRequest, HooksService
from hbs_ads.features.ingest.service import IngestRunRequest, IngestService
from hbs_ads.features.tagging.service import (
    AutoTagRequest,
    PendingTagsRequest,
    TagAIRequest,
    TaggingService,
)
from hbs_ads.features.trim.service import TrimRunRequest, TrimService
from hbs_ads.features.variants.service import (
    AssembleVariantRequest,
    ExportVariantRequest,
    GenerateVariantsRequest,
    ValidateVariantRequest,
    VariantsService,
)


@dataclass(slots=True)
class PipelineRunRequest:
    workspace_root: Path
    trim_only: bool = False
    ingest_only: bool = False
    dry_run: bool = False


class PipelineService:
    def __init__(
        self,
        ingest: IngestService,
        trim: TrimService,
        tagging: TaggingService,
        variants: VariantsService,
        hooks: HooksService,
    ) -> None:
        self.ingest = ingest
        self.trim = trim
        self.tagging = tagging
        self.variants = variants
        self.hooks = hooks

    def run(self, request: PipelineRunRequest) -> CommandResult:
        if request.trim_only and request.ingest_only:
            raise AppError("pipeline run accepts at most one explicit mode flag")

        mode = "trim" if request.trim_only else "ingest" if request.ingest_only else "full"
        state_path = request.workspace_root / "logs" / "pipeline-state.json"
        if request.ingest_only:
            result = self.ingest.run(
                IngestRunRequest(workspace_root=request.workspace_root, dry_run=request.dry_run)
            )
            return self._result_with_state(
                message="pipeline run completed in ingest mode",
                status=result.status,
                state_path=state_path,
                dry_run=request.dry_run,
                data={
                    "mode": mode,
                    "blocked": False,
                    "stages": [{"stage": "ingest", "status": result.status, "message": result.message}],
                    "allowed_next_stages": ["trim", "tag auto"],
                    "authoritative_artifacts": {"raw_assets_dir": str(request.workspace_root / "_ASSETS" / "raw")},
                },
            )

        if request.trim_only:
            config_path = request.workspace_root / "cuts.json"
            if not config_path.exists():
                raise AppError("pipeline trim mode requires cuts.json in the workspace root")
            result = self.trim.run(
                TrimRunRequest(
                    workspace_root=request.workspace_root,
                    config_path=config_path,
                    dry_run=request.dry_run,
                )
            )
            return self._result_with_state(
                message="pipeline run completed in trim mode",
                status=result.status,
                state_path=state_path,
                dry_run=request.dry_run,
                data={
                    "mode": mode,
                    "blocked": False,
                    "stages": [{"stage": "trim", "status": result.status, "message": result.message}],
                    "allowed_next_stages": ["tag auto", "tag ai", "tag approve --all"],
                    "authoritative_artifacts": {"cuts_path": str(config_path)},
                },
            )

        stages: list[dict[str, object]] = []
        ingest_result = self.ingest.run(
            IngestRunRequest(workspace_root=request.workspace_root, dry_run=request.dry_run)
        )
        stages.append({"stage": "ingest", "status": ingest_result.status, "message": ingest_result.message})
        if ingest_result.status not in ("ok", "planned"):
            return self._result_with_state(
                message="pipeline failed at ingest stage",
                status="failed",
                state_path=request.workspace_root / "logs" / "pipeline-state.json",
                dry_run=request.dry_run,
                data={"mode": "full", "blocked": False, "stages": stages, "failed_at": "ingest"},
            )

        cuts_path = request.workspace_root / "cuts.json"
        if cuts_path.exists():
            trim_result = self.trim.run(
                TrimRunRequest(
                    workspace_root=request.workspace_root,
                    config_path=cuts_path,
                    dry_run=request.dry_run,
                )
            )
            stages.append({"stage": "trim", "status": trim_result.status, "message": trim_result.message})

        pending_before = self.tagging.pending(PendingTagsRequest(workspace_root=request.workspace_root))
        if pending_before.data.get("pending"):
            if request.dry_run:
                stages.append({"stage": "tag:auto", "status": "ok", "message": "tag auto planned"})
                stages.append({"stage": "tag:ai", "status": "ok", "message": "tag ai planned"})
                return self._result_with_state(
                    message="pipeline run blocked at review gate",
                    status="blocked",
                    state_path=state_path,
                    dry_run=True,
                    data={
                        "mode": mode,
                        "blocked": True,
                        "stages": stages,
                        "review_required": pending_before.data["pending"],
                        "allowed_next_stages": ["tag approve --all", "pipeline run"],
                        "authoritative_artifacts": {"pending_clips": pending_before.data["pending"]},
                    },
                )
            auto_result = self.tagging.auto(AutoTagRequest(workspace_root=request.workspace_root))
            ai_result = self.tagging.ai(TagAIRequest(workspace_root=request.workspace_root))
            stages.append({"stage": "tag:auto", "status": auto_result.status, "message": auto_result.message})
            stages.append({"stage": "tag:ai", "status": ai_result.status, "message": ai_result.message})

        pending_after = self.tagging.pending(PendingTagsRequest(workspace_root=request.workspace_root))
        if pending_after.data.get("pending"):
            return self._result_with_state(
                message="pipeline run blocked at review gate",
                status="blocked",
                state_path=state_path,
                dry_run=request.dry_run,
                data={
                    "mode": mode,
                    "blocked": True,
                    "stages": stages,
                    "review_required": pending_after.data["pending"],
                    "allowed_next_stages": ["tag approve --all", "pipeline run"],
                    "authoritative_artifacts": {"pending_clips": pending_after.data["pending"]},
                },
            )

        generated = self.variants.generate(
            GenerateVariantsRequest(workspace_root=request.workspace_root, dry_run=request.dry_run)
        )
        stages.append({"stage": "variants:generate", "status": generated.status, "message": generated.message})
        planned_variants = [str(name) for name in generated.data.get("variants", [])]

        if request.dry_run:
            if planned_variants:
                stages.append(
                    {
                        "stage": "hooks:assemble",
                        "status": "ok",
                        "message": "hooks assemble planned for pipeline-hook",
                    }
                )
                stages.append(
                    {
                        "stage": "variants:assemble",
                        "status": "ok",
                        "message": f"variants assemble planned for {len(planned_variants)} variants",
                    }
                )
                stages.append(
                    {
                        "stage": "variants:export",
                        "status": "ok",
                        "message": f"variants export planned for {planned_variants[0]}",
                    }
                )
                stages.append(
                    {
                        "stage": "variants:validate",
                        "status": "ok",
                        "message": "variants validate planned for generic",
                    }
                )
            return self._result_with_state(
                message=f"pipeline run planned in {mode} mode",
                status="ok",
                state_path=state_path,
                dry_run=True,
                data={
                    "mode": mode,
                    "blocked": False,
                    "stages": stages,
                    "variants": planned_variants,
                    "allowed_next_stages": ["pipeline run", "tag approve --all"],
                    "authoritative_artifacts": {
                        "variant_configs": generated.data.get("configs", []),
                    },
                },
            )

        configs = [Path(path) for path in generated.data.get("configs", [])]
        assembled_variants: list[str] = []
        for config_path in configs:
            assemble_result = self.variants.assemble(
                AssembleVariantRequest(
                    workspace_root=request.workspace_root,
                    config_path=config_path,
                    dry_run=request.dry_run,
                )
            )
            stages.append({"stage": "variants:assemble", "status": assemble_result.status, "message": assemble_result.message})
            for variant in assemble_result.data.get("variants", []):
                variant_name = str(variant["variant"])
                assembled_variants.append(variant_name)
                export_result = self.variants.export(
                    ExportVariantRequest(
                        workspace_root=request.workspace_root,
                        variant=variant_name,
                        dry_run=request.dry_run,
                    )
                )
                stages.append(
                    {
                        "stage": "variants:export",
                        "status": export_result.status,
                        "message": export_result.message,
                        "variant": variant_name,
                    }
                )

        if assembled_variants:
            approved_hooks = self._has_hook_candidates(request.workspace_root)
            if approved_hooks:
                hook_result = self.hooks.assemble(
                    AssembleHookRequest(
                        workspace_root=request.workspace_root,
                        name="pipeline-hook",
                        dry_run=request.dry_run,
                    )
                )
                stages.append({"stage": "hooks:assemble", "status": hook_result.status, "message": hook_result.message})

        validated = self.variants.validate(
            ValidateVariantRequest(workspace_root=request.workspace_root, platform="generic")
        )
        stages.append({"stage": "variants:validate", "status": validated.status, "message": validated.message})
        return self._result_with_state(
            message=f"pipeline run completed in {mode} mode",
            status="ok",
            state_path=state_path,
            dry_run=request.dry_run,
            data={
                "mode": mode,
                "blocked": False,
                "stages": stages,
                "variants": assembled_variants,
                "allowed_next_stages": ["variants archive", "sharepoint upload", "pipeline run"],
                "authoritative_artifacts": {
                    "variant_configs": generated.data.get("configs", []),
                    "validated_variants": validated.data.get("results", []),
                },
            },
        )

    def _has_hook_candidates(self, workspace_root: Path) -> bool:
        pending = self.tagging.pending(PendingTagsRequest(workspace_root=workspace_root))
        if pending.data.get("pending"):
            return False
        return True

    def _result_with_state(
        self,
        *,
        message: str,
        status: str,
        state_path: Path,
        dry_run: bool,
        data: dict[str, object],
    ) -> CommandResult:
        state = {**data, "state_file": str(state_path), "dry_run": dry_run}
        if not dry_run:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return CommandResult(status=status, message=message, data=state)
