from __future__ import annotations

from dataclasses import dataclass
import json
import re
import shutil
from pathlib import Path

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.core.outputs import CommandResult
from hbs_ads.core.workspace import WorkspaceManager
from hbs_ads.infra.db.sqlite import ClipRecord, SQLiteDatabase, VariantRecord
from hbs_ads.infra.exec.runner import CommandRunner


@dataclass(slots=True)
class GenerateVariantsRequest:
    workspace_root: Path
    max_body: int | None = None
    dry_run: bool = False


@dataclass(slots=True)
class AssembleVariantRequest:
    workspace_root: Path
    config_path: Path
    dry_run: bool = False


@dataclass(slots=True)
class ExportVariantRequest:
    workspace_root: Path
    variant: str
    dry_run: bool = False


@dataclass(slots=True)
class ValidateVariantRequest:
    workspace_root: Path
    platform: str


@dataclass(slots=True)
class ArchiveVariantRequest:
    workspace_root: Path
    variant: str
    dry_run: bool = False


@dataclass(slots=True)
class VariantConfig:
    name: str
    clips: list[str]


@dataclass(slots=True)
class MediaProbe:
    width: int
    height: int
    has_audio: bool


class VariantsService:
    def __init__(
        self,
        settings: ResolvedSettings,
        workspace: WorkspaceManager,
        database: SQLiteDatabase,
        command_runner: CommandRunner,
    ) -> None:
        self.settings = settings
        self.workspace = workspace
        self.database = database
        self.command_runner = command_runner

    def generate(self, request: GenerateVariantsRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        approved = [clip for clip in self.database.list_clips() if clip.approved]
        if not approved:
            raise AppError("variants generate requires approved clips")

        hooks = [clip for clip in approved if self._is_hook_clip(clip)]
        bodies = [clip for clip in approved if clip.kind in {"raw", "trimmed"} and not self._is_hook_clip(clip)]
        max_body = request.max_body or max(1, len(bodies))
        configs = self._build_configs(hooks=hooks, bodies=bodies, max_body=max_body)
        if not configs:
            raise AppError("variants generate produced no valid configs")

        written: list[str] = []
        for config in configs:
            config_path = layout.generated_variants_dir / f"{self._slugify(config.name)}.json"
            payload = {
                "variant": config.name,
                "clips": [{"clip": clip} for clip in config.clips],
            }
            if not request.dry_run:
                config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
                self.database.upsert_variant(
                    VariantRecord(
                        name=config.name,
                        config_path=str(config_path),
                        status="generated",
                        metadata={"clips": config.clips},
                    )
                )
            written.append(str(config_path))
        return CommandResult(
            status="ok",
            message=(
                f"variants generate {'planned' if request.dry_run else 'completed'} "
                f"with {len(configs)} configs"
            ),
            data={
                "configs": written,
                "variants": [config.name for config in configs],
                "dry_run": request.dry_run,
                "max_body": request.max_body,
            },
        )

    def assemble(self, request: AssembleVariantRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        resolved_config = self._resolve_path(layout.root, request.config_path)
        configs = self._load_configs(resolved_config)
        assembled: list[dict[str, object]] = []
        for config in configs:
            resolved_clips = [str(self._resolve_clip(layout, clip)) for clip in config.clips]
            variant_dir = layout.variants_dir / config.name
            render_path = variant_dir / "render-master.mp4"
            manifest_path = variant_dir / "manifest.json"
            placeholder_mode = self._should_use_placeholder_mode([Path(path) for path in resolved_clips])
            if not request.dry_run:
                variant_dir.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(
                    json.dumps(
                        {
                            "variant": config.name,
                            "config_path": str(resolved_config),
                            "clips": resolved_clips,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                if placeholder_mode:
                    render_path.write_text(
                        "\n".join([f"variant={config.name}", *resolved_clips]) + "\n",
                        encoding="utf-8",
                    )
                else:
                    self._assemble_real_variant(
                        clip_paths=[Path(path) for path in resolved_clips],
                        output_path=render_path,
                        cwd=layout.root,
                    )
                self.database.upsert_variant(
                    VariantRecord(
                        name=config.name,
                        config_path=str(resolved_config),
                        status="assembled",
                        render_path=str(render_path),
                        metadata={
                            "clips": resolved_clips,
                            "manifest_path": str(manifest_path),
                            "render_mode": "placeholder" if placeholder_mode else "ffmpeg",
                        },
                    )
                )
            assembled.append(
                {
                    "variant": config.name,
                    "render_path": str(render_path),
                    "clips": resolved_clips,
                    "render_mode": "placeholder" if placeholder_mode else "ffmpeg",
                }
            )
        return CommandResult(
            status="ok",
            message=(
                f"variants assemble {'planned' if request.dry_run else 'completed'} "
                f"for {len(assembled)} variants"
            ),
            data={"variants": assembled, "config_path": str(resolved_config), "dry_run": request.dry_run},
        )

    def export(self, request: ExportVariantRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        record = self.database.get_variant(request.variant)
        if record is None:
            raise AppError(f"variant not found: {request.variant}")
        render_path = Path(record.render_path)
        if not record.render_path or (not request.dry_run and not render_path.exists()):
            raise AppError(f"variant render missing: {request.variant}")

        export_dir = layout.variants_dir / request.variant / "export"
        export_path = export_dir / f"{request.variant}.mp4"
        placeholder_mode = not self._is_media_file(render_path)
        if not request.dry_run:
            export_dir.mkdir(parents=True, exist_ok=True)
            if placeholder_mode:
                shutil.copyfile(render_path, export_path)
            else:
                self._export_real_variant(
                    master_file=render_path,
                    output_path=export_path,
                    cwd=layout.root,
                )
            self.database.upsert_variant(
                VariantRecord(
                    name=record.name,
                    config_path=record.config_path,
                    status="exported",
                    render_path=record.render_path,
                    export_paths=[str(export_path)],
                    archive_path=record.archive_path,
                    metadata=record.metadata,
                )
            )
        return CommandResult(
            status="ok",
            message=(
                f"variants export {'planned' if request.dry_run else 'completed'} "
                f"for {request.variant}"
            ),
            data={
                "variant": request.variant,
                "export_path": str(export_path),
                "dry_run": request.dry_run,
                "export_mode": "placeholder-copy" if placeholder_mode else "ffmpeg",
            },
        )

    def validate(self, request: ValidateVariantRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        results: list[dict[str, object]] = []
        for record in self.database.list_variants():
            candidate = Path((record.export_paths or [record.render_path])[0]) if (record.export_paths or record.render_path) else None
            valid = candidate is not None and candidate.exists() and candidate.suffix == ".mp4"
            validation_path = layout.variants_dir / record.name / f"validation-{request.platform}.json"
            payload = {
                "variant": record.name,
                "platform": request.platform,
                "artifact": str(candidate) if candidate else "",
                "valid": valid,
            }
            validation_path.parent.mkdir(parents=True, exist_ok=True)
            validation_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            if valid:
                self.database.upsert_variant(
                    VariantRecord(
                        name=record.name,
                        config_path=record.config_path,
                        status="validated",
                        render_path=record.render_path,
                        export_paths=record.export_paths,
                        archive_path=record.archive_path,
                        metadata={**(record.metadata or {}), "validation_path": str(validation_path)},
                    )
                )
            results.append(payload)
        if not results:
            raise AppError("variants validate found no generated variants")
        return CommandResult(
            status="ok",
            message=(
                f"variants validate completed for {len(results)} variants on {request.platform}"
            ),
            data={"platform": request.platform, "results": results},
        )

    def archive(self, request: ArchiveVariantRequest) -> CommandResult:
        layout = self.workspace.initialize(self.settings)
        record = self.database.get_variant(request.variant)
        if record is None:
            raise AppError(f"variant not found: {request.variant}")
        source_dir = layout.variants_dir / request.variant
        if not request.dry_run and not source_dir.exists():
            raise AppError(f"variant directory missing: {request.variant}")

        archive_dir = layout.archive_dir / request.variant
        if not request.dry_run:
            if archive_dir.exists():
                shutil.rmtree(archive_dir)
            shutil.copytree(source_dir, archive_dir)
            self.database.upsert_variant(
                VariantRecord(
                    name=record.name,
                    config_path=record.config_path,
                    status="archived",
                    render_path=record.render_path,
                    export_paths=record.export_paths,
                    archive_path=str(archive_dir),
                    metadata=record.metadata,
                )
            )
        return CommandResult(
            status="ok",
            message=(
                f"variants archive {'planned' if request.dry_run else 'completed'} "
                f"for {request.variant}"
            ),
            data={"variant": request.variant, "archive_path": str(archive_dir), "dry_run": request.dry_run},
        )

    def _build_configs(
        self,
        *,
        hooks: list[ClipRecord],
        bodies: list[ClipRecord],
        max_body: int,
    ) -> list[VariantConfig]:
        configs: list[VariantConfig] = []
        if hooks and bodies:
            for hook in hooks:
                for body in bodies[:max_body]:
                    configs.append(
                        VariantConfig(
                            name=f"{self._variant_label(hook.path)}-{self._variant_label(body.path)}",
                            clips=[hook.path, body.path],
                        )
                    )
        elif bodies:
            for body in bodies[:max_body]:
                configs.append(
                    VariantConfig(
                        name=self._variant_label(body.path),
                        clips=[body.path],
                    )
                )
        elif hooks:
            for hook in hooks[:max_body]:
                configs.append(
                    VariantConfig(
                        name=self._variant_label(hook.path),
                        clips=[hook.path],
                    )
                )
        return configs

    def _load_configs(self, config_path: Path) -> list[VariantConfig]:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = [payload]
        configs: list[VariantConfig] = []
        for entry in payload:
            name = entry.get("variant", "").strip()
            clips_data = entry.get("clips", [])
            clips = [clip["clip"] if isinstance(clip, dict) else clip for clip in clips_data]
            if not name:
                raise AppError(f"variant config missing variant name: {config_path}")
            if not clips:
                raise AppError(f"variant config has no clips: {config_path}")
            configs.append(VariantConfig(name=name, clips=clips))
        return configs

    def _resolve_clip(self, layout, clip: str) -> Path:
        candidate = Path(clip)
        candidates = [
            candidate,
            layout.root / candidate,
            layout.trimmed_assets_dir / candidate.name,
            layout.raw_assets_dir / candidate.name,
            layout.hooks_dir / candidate.name,
            layout.inbox_dir / candidate.name,
        ]
        for path in candidates:
            if path.exists() and path.is_file():
                return path.resolve()
        raise AppError(f"clip not found: {clip}")

    def _resolve_path(self, root: Path, path: Path) -> Path:
        return path if path.is_absolute() else (root / path).resolve()

    def _should_use_placeholder_mode(self, clip_paths: list[Path]) -> bool:
        return not all(self._probe_media(path) is not None for path in clip_paths)

    def _is_media_file(self, path: Path) -> bool:
        return self._probe_media(path) is not None

    def _probe_media(self, path: Path) -> MediaProbe | None:
        command = [
            self.settings.tools.ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ]
        result = self.command_runner.run(command)
        if result.returncode != 0:
            return None
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return None
        streams = payload.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        if video_stream is None:
            return None
        return MediaProbe(
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
        )

    def _assemble_real_variant(
        self,
        *,
        clip_paths: list[Path],
        output_path: Path,
        cwd: Path,
    ) -> None:
        first_probe = self._probe_media(clip_paths[0])
        if first_probe is None:
            raise AppError(f"variant assemble probe failed: {clip_paths[0]}")
        if not all((probe := self._probe_media(path)) and probe.has_audio for path in clip_paths):
            raise AppError("variant assemble requires clips with both video and audio streams")

        ffmpeg_args: list[str] = [self.settings.tools.ffmpeg, "-y"]
        for clip_path in clip_paths:
            ffmpeg_args.extend(["-i", str(clip_path)])

        filter_parts: list[str] = []
        concat_inputs: list[str] = []
        for index, _clip_path in enumerate(clip_paths):
            filter_parts.append(
                f"[{index}:v]scale={first_probe.width}:{first_probe.height}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={first_probe.width}:{first_probe.height}:(ow-iw)/2:(oh-ih)/2,"
                f"setsar=1,fps=30[v{index}]"
            )
            filter_parts.append(
                f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=48000:"
                f"channel_layouts=stereo[a{index}]"
            )
            concat_inputs.append(f"[v{index}][a{index}]")

        filter_complex = ";".join(filter_parts + [f"{''.join(concat_inputs)}concat=n={len(clip_paths)}:v=1:a=1[outv][outa]"])
        ffmpeg_args.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-map",
                "[outa]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-colorspace",
                "bt709",
                "-color_trc",
                "bt709",
                "-color_primaries",
                "bt709",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
            ]
        )
        result = self.command_runner.run(ffmpeg_args, cwd=cwd)
        if result.returncode != 0:
            raise AppError(f"variant assemble failed: {result.stderr.strip() or result.returncode}")

    def _export_real_variant(
        self,
        *,
        master_file: Path,
        output_path: Path,
        cwd: Path,
    ) -> None:
        ffmpeg_args = [
            self.settings.tools.ffmpeg,
            "-y",
            "-i",
            str(master_file),
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-preset",
            "slow",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        result = self.command_runner.run(ffmpeg_args, cwd=cwd)
        if result.returncode != 0:
            raise AppError(f"variant export failed: {result.stderr.strip() or result.returncode}")

    def _is_hook_clip(self, clip: ClipRecord) -> bool:
        text = f"{Path(clip.path).stem} {' '.join(clip.tags or [])}".lower()
        return any(token in text for token in ("hook", "intro", "question"))

    def _variant_label(self, value: str) -> str:
        stem = Path(value).stem
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-")
        return cleaned or "variant"

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "variant"
