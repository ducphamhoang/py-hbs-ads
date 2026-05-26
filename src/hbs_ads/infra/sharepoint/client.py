from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import time
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen
import uuid

from hbs_ads.app.settings import ResolvedSettings
from hbs_ads.core.errors import AppError
from hbs_ads.infra.exec.runner import CommandRunner


DEVICE_CODE_APP_ID = "9bc3ab49-b65d-410a-85ad-de819febfddc"
CHUNK_SIZE = 4_000_000


@dataclass(slots=True)
class SharePointSetupResult:
    mode: str
    remote_root: str
    site_title: str = ""


@dataclass(slots=True)
class SharePointRemoteFile:
    name: str
    server_relative_url: str
    size_bytes: int | None = None
    modified_at: str = ""
    folder: str = ""


@dataclass(slots=True)
class SharePointDownloadResult:
    remote_file: str
    downloaded_file: str
    size_bytes: int | None = None
    folder: str = ""
    dry_run: bool = False


@dataclass(slots=True)
class SharePointUploadResult:
    local_file: str
    remote_file: str
    remote_folder: str
    share_url: str
    dry_run: bool = False


class SharePointClient(Protocol):
    mode: str

    def setup(self) -> SharePointSetupResult: ...

    def list_files(self, query: str, target: str | None = None) -> list[SharePointRemoteFile]: ...

    def download_files(
        self,
        *,
        query: str,
        exact_file_url: str,
        destination_dir: Path,
        dry_run: bool,
        target: str | None = None,
    ) -> list[SharePointDownloadResult]: ...

    def upload_file(self, *, local_path: Path, variant: str, dry_run: bool) -> SharePointUploadResult: ...


@dataclass(slots=True)
class FileBackedSharePointClient:
    settings: ResolvedSettings

    @property
    def mode(self) -> str:
        return "file-backed"

    def setup(self) -> SharePointSetupResult:
        remote_root = self._remote_root()
        remote_root.mkdir(parents=True, exist_ok=True)
        return SharePointSetupResult(mode=self.mode, remote_root=str(remote_root))

    def list_files(self, query: str, target: str | None = None) -> list[SharePointRemoteFile]:
        needle = self._safe_segment(query)
        matches: list[SharePointRemoteFile] = []
        for path in sorted(candidate for candidate in self._remote_root().rglob("*") if candidate.is_file()):
            folder_slug = self._safe_segment(path.parent.name)
            stem_slug = self._safe_segment(path.stem)
            if needle and needle not in folder_slug and needle not in stem_slug:
                continue
            relative_path = path.relative_to(self._library_root()).as_posix()
            matches.append(
                SharePointRemoteFile(
                    name=path.name,
                    server_relative_url=f"/{relative_path}",
                    size_bytes=path.stat().st_size,
                    folder=path.parent.name,
                )
            )
        return matches

    def download_files(
        self,
        *,
        query: str,
        exact_file_url: str,
        destination_dir: Path,
        dry_run: bool,
        target: str | None = None,
    ) -> list[SharePointDownloadResult]:
        if exact_file_url:
            source = self._local_path_from_server_relative(exact_file_url)
            if not source.exists():
                raise AppError(f"sharepoint download source not found: {exact_file_url}")
            return [self._copy_to_destination(source=source, destination_dir=destination_dir, dry_run=dry_run)]

        matches = self.list_files(query)
        if not matches:
            raise AppError("sharepoint download source not found; run sharepoint upload first or provide a known variant")
        results: list[SharePointDownloadResult] = []
        for match in matches:
            results.append(
                self._copy_to_destination(
                    source=self._local_path_from_server_relative(match.server_relative_url),
                    destination_dir=destination_dir,
                    dry_run=dry_run,
                )
            )
        return results

    def upload_file(self, *, local_path: Path, variant: str, dry_run: bool) -> SharePointUploadResult:
        remote_dir = self._remote_root() / self._safe_segment(variant)
        remote_file = remote_dir / local_path.name
        if not dry_run:
            remote_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, remote_file)
        return SharePointUploadResult(
            local_file=str(local_path),
            remote_file=str(remote_file),
            remote_folder=str(remote_dir),
            share_url=str(remote_dir),
            dry_run=dry_run,
        )

    def _copy_to_destination(self, *, source: Path, destination_dir: Path, dry_run: bool) -> SharePointDownloadResult:
        destination = destination_dir / source.name
        if not dry_run:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return SharePointDownloadResult(
            remote_file=str(source),
            downloaded_file=str(destination),
            size_bytes=source.stat().st_size if source.exists() else None,
            folder=source.parent.name,
            dry_run=dry_run,
        )

    def _library_root(self) -> Path:
        return self.settings.workspace.root / "sharepoint" / "library"

    def _remote_root(self) -> Path:
        return self._library_root() / Path(*self._base_parts())

    def _local_path_from_server_relative(self, server_relative_url: str) -> Path:
        relative = server_relative_url.lstrip("/")
        return self._library_root() / Path(relative)

    def _base_parts(self) -> list[str]:
        return [segment.strip() for segment in self.settings.sharepoint.base_path.split("/") if segment.strip()]

    def _safe_segment(self, value: str) -> str:
        slug = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
        return "-".join(part for part in slug.split("-") if part)


@dataclass(slots=True)
class M365SharePointClient:
    settings: ResolvedSettings
    command_runner: CommandRunner

    @property
    def mode(self) -> str:
        return "live"

    def setup(self) -> SharePointSetupResult:
        self._run_m365_login()
        token = self._get_token()
        payload = self._request_json(
            f"{self.settings.sharepoint.site_url}/_api/web?$select=Title",
            token=token,
        )
        title = str(payload["d"]["Title"])
        return SharePointSetupResult(
            mode=self.mode,
            remote_root=f"{self.settings.sharepoint.site_url.rstrip('/')}/{self.settings.sharepoint.base_path.strip('/')}",
            site_title=title,
        )

    def list_files(self, query: str, target: str | None = None) -> list[SharePointRemoteFile]:
        import re as _re

        token = self._get_token()
        folder_server_rel = self._base_folder_server_relative(target)
        subfolders = self._request_json(
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl('{self._sp_enc(folder_server_rel)}')"
            "/Folders?$select=Name,ServerRelativeUrl&$top=500",
            token=token,
        )["d"]["results"]
        needle = query.lower()
        # Base part of needle (e.g. "v342" from "v342-01") for broader parent-folder matching
        base_m = _re.match(r"^(v\d+)", needle)
        needle_base = base_m.group(1) if base_m else needle
        matches: list[SharePointRemoteFile] = []
        for folder in subfolders:
            folder_name = str(folder["Name"])
            folder_url = unquote(str(folder["ServerRelativeUrl"]))
            folder_name_lower = folder_name.lower()
            folder_matches_query = not needle or needle in folder_name_lower
            folder_matches_base = bool(needle_base) and needle_base in folder_name_lower

            if folder_matches_query:
                self._collect_files(token, folder_url, folder_name, needle="", matches=matches)
            elif folder_matches_base:
                # Folder name contains the base variant — scan files filtered by full needle
                self._collect_files(token, folder_url, folder_name, needle=needle, matches=matches)

            # One level deeper: subfolders inside this folder
            sub_subfolders = self._request_json(
                f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
                f"('{self._sp_enc(folder_url)}')"
                "/Folders?$select=Name,ServerRelativeUrl&$top=500",
                token=token,
            )["d"]["results"]
            for sub in sub_subfolders:
                sub_name = str(sub["Name"])
                sub_url = unquote(str(sub["ServerRelativeUrl"]))
                sub_name_lower = sub_name.lower()
                # Full match on parent or sub folder name
                if not needle or needle in folder_name_lower or needle in sub_name_lower:
                    self._collect_files(token, sub_url, sub_name, needle="", matches=matches)
                elif folder_matches_base:
                    # Parent matches base variant — scan files filtered by full needle
                    self._collect_files(token, sub_url, sub_name, needle=needle, matches=matches)

        return matches

    def _collect_files(
        self,
        token: str,
        folder_url: str,
        folder_display_name: str,
        needle: str,
        matches: list[SharePointRemoteFile],
    ) -> None:
        files = self._request_json(
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
            f"('{self._sp_enc(folder_url)}')"
            "/Files?$select=Name,ServerRelativeUrl,Length,TimeLastModified&$top=500",
            token=token,
        )["d"]["results"]
        for candidate in files:
            name = str(candidate["Name"])
            if not name.lower().endswith(".mp4"):
                continue
            if needle and needle not in name.lower():
                continue
            matches.append(
                SharePointRemoteFile(
                    name=name,
                    server_relative_url=unquote(str(candidate["ServerRelativeUrl"])),
                    size_bytes=int(candidate.get("Length", 0) or 0),
                    modified_at=str(candidate.get("TimeLastModified", "")),
                    folder=folder_display_name,
                )
            )

    def download_files(
        self,
        *,
        query: str,
        exact_file_url: str,
        destination_dir: Path,
        dry_run: bool,
        target: str | None = None,
    ) -> list[SharePointDownloadResult]:
        if exact_file_url:
            return [self._download_one(exact_file_url, destination_dir=destination_dir, dry_run=dry_run)]

        matches = self.list_files(query, target=target)
        if not matches:
            raise AppError(f"sharepoint list found no remote files for query: {query}")
        return [
            self._download_one(item.server_relative_url, destination_dir=destination_dir, dry_run=dry_run, folder=item.folder)
            for item in matches
        ]

    def upload_file(self, *, local_path: Path, variant: str, dry_run: bool) -> SharePointUploadResult:
        folder_server_rel = f"{self._base_folder_server_relative(variant)}/{self._safe_segment(variant)}"
        remote_file = f"{folder_server_rel}/{local_path.name}"
        share_url = f"{self._site_root()}{folder_server_rel}"
        if dry_run:
            return SharePointUploadResult(
                local_file=str(local_path),
                remote_file=remote_file,
                remote_folder=folder_server_rel,
                share_url=share_url,
                dry_run=True,
            )

        token = self._get_token()
        self._ensure_folder(token, folder_server_rel)
        if local_path.stat().st_size <= CHUNK_SIZE:
            self._upload_small_file(token, folder_server_rel, local_path)
        else:
            self._chunked_upload(token, folder_server_rel, local_path)
        return SharePointUploadResult(
            local_file=str(local_path),
            remote_file=remote_file,
            remote_folder=folder_server_rel,
            share_url=share_url,
            dry_run=False,
        )

    def _download_one(
        self,
        server_relative_url: str,
        *,
        destination_dir: Path,
        dry_run: bool,
        folder: str = "",
    ) -> SharePointDownloadResult:
        filename = Path(unquote(server_relative_url)).name
        destination = destination_dir / filename
        if dry_run:
            return SharePointDownloadResult(
                remote_file=server_relative_url,
                downloaded_file=str(destination),
                folder=folder,
                dry_run=True,
            )

        token = self._get_token()
        destination_dir.mkdir(parents=True, exist_ok=True)
        url = (
            f"{self.settings.sharepoint.site_url}/_api/web/GetFileByServerRelativeUrl"
            f"('{self._sp_enc(server_relative_url)}')/$value"
        )
        with urlopen(Request(url, headers=self._headers(token)), timeout=120) as response:
            destination.write_bytes(response.read())
        return SharePointDownloadResult(
            remote_file=server_relative_url,
            downloaded_file=str(destination),
            size_bytes=destination.stat().st_size,
            folder=folder,
            dry_run=False,
        )

    def _run_m365_login(self) -> None:
        import subprocess

        result = subprocess.run(
            [
                self.settings.tools.m365,
                "login",
                "--authType",
                "deviceCode",
                "--appId",
                DEVICE_CODE_APP_ID,
                "--tenant",
                self.settings.sharepoint.tenant_id,
            ],
            cwd=str(self.settings.workspace.root),
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise AppError(f"sharepoint setup failed: exit code {result.returncode}")

    def _get_token(self) -> str:
        result = self.command_runner.run(
            [
                self.settings.tools.m365,
                "util",
                "accesstoken",
                "get",
                "--resource",
                self._site_root(),
                "--output",
                "text",
            ],
            cwd=self.settings.workspace.root,
            timeout=60,
        )
        if result.returncode != 0:
            raise AppError(
                f"m365 token fetch failed: {result.stderr.strip() or result.returncode}. "
                f"Run `{self.settings.tools.m365} login` or `hbs-ads sharepoint setup`."
            )
        token = result.stdout.strip()
        if not token:
            raise AppError("m365 returned an empty token")
        return token

    def _ensure_folder(self, token: str, folder_server_rel: str) -> None:
        url = (
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
            f"('{self._sp_enc(folder_server_rel)}')"
        )
        try:
            self._request_json(url, token=token)
            return
        except AppError as exc:
            if "HTTP 404" not in str(exc):
                raise

        parent_rel = "/".join(folder_server_rel.rstrip("/").split("/")[:-1])
        folder_name = folder_server_rel.rstrip("/").split("/")[-1]
        create_url = (
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
            f"('{self._sp_enc(parent_rel)}')/Folders/add('{self._sp_enc(folder_name)}')"
        )
        self._request_json(create_url, token=token, method="POST", content_type="application/json;odata=verbose")

    def _upload_small_file(self, token: str, folder_server_rel: str, local_path: Path) -> None:
        url = (
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
            f"('{self._sp_enc(folder_server_rel)}')/Files/add(url='{self._sp_enc(local_path.name)}',overwrite=true)"
        )
        self._request_json(
            url,
            token=token,
            method="POST",
            content_type="application/octet-stream",
            body=local_path.read_bytes(),
        )

    def _chunked_upload(self, token: str, folder_server_rel: str, local_path: Path) -> None:
        upload_id = str(uuid.uuid4())
        file_server_rel = f"{folder_server_rel}/{local_path.name}"
        create_url = (
            f"{self.settings.sharepoint.site_url}/_api/web/GetFolderByServerRelativeUrl"
            f"('{self._sp_enc(folder_server_rel)}')/Files/add(url='{self._sp_enc(local_path.name)}',overwrite=true)"
        )
        self._request_json(
            create_url,
            token=token,
            method="POST",
            content_type="application/octet-stream",
            body=b"",
        )
        file_size = local_path.stat().st_size
        offset = 0
        with local_path.open("rb") as handle:
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                is_last = handle.tell() >= file_size
                if offset == 0:
                    endpoint = f"StartUpload(uploadId=guid'{upload_id}')"
                elif is_last:
                    endpoint = f"FinishUpload(uploadId=guid'{upload_id}',fileOffset={offset})"
                else:
                    endpoint = f"ContinueUpload(uploadId=guid'{upload_id}',fileOffset={offset})"
                url = (
                    f"{self.settings.sharepoint.site_url}/_api/web/GetFileByServerRelativeUrl"
                    f"('{self._sp_enc(file_server_rel)}')/{endpoint}"
                )
                self._request_json(
                    url,
                    token=token,
                    method="POST",
                    content_type="application/octet-stream",
                    body=chunk,
                )
                offset += len(chunk)

    def _request_json(
        self,
        url: str,
        *,
        token: str,
        method: str = "GET",
        content_type: str | None = None,
        body: bytes | None = None,
        max_retries: int = 3,
    ) -> dict[str, object]:
        headers = self._headers(token, content_type=content_type)
        request = Request(url, data=body, headers=headers, method=method)
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                with urlopen(request, timeout=120) as response:
                    payload = response.read().decode("utf-8")
                    return json.loads(payload) if payload else {}
            except HTTPError as exc:
                if exc.code == 429 and attempt < max_retries - 1:
                    retry_after = int(exc.headers.get("Retry-After", 5))
                    time.sleep(min(retry_after, 60))
                    continue
                message = exc.read().decode("utf-8", errors="replace")
                raise AppError(f"SharePoint request failed with HTTP {exc.code}: {message}") from exc
            except URLError as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise AppError(f"SharePoint request failed: {exc.reason}") from exc
        if last_exc:
            raise AppError(f"SharePoint request failed after {max_retries} retries") from last_exc
        return {}

    def _headers(self, token: str, *, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;odata=verbose",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _site_root(self) -> str:
        parsed = urlparse(self.settings.sharepoint.site_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _site_path(self) -> str:
        return urlparse(self.settings.sharepoint.site_url).path.rstrip("/")

    def _base_folder_server_relative(self, target: str | None = None) -> str:
        base_path = self.settings.sharepoint.resolve_base_path(target)
        return f"{self._site_path()}/{base_path.strip('/')}"

    def _sp_enc(self, path: str) -> str:
        return quote(path.replace("'", "''"), safe="/")

    def _safe_segment(self, value: str) -> str:
        slug = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
        return "-".join(part for part in slug.split("-") if part) or "default"
