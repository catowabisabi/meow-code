"""
Files API client for managing files.

This module provides functionality to download and upload files to Anthropic Public Files API.
Used by the Claude Code agent to download file attachments at session startup.
"""

import asyncio
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

import httpx


FILES_API_BETA_HEADER = "files-api-2025-04-14,oauth-2025-04-20"
ANTHROPIC_VERSION = "2023-06-01"
MAX_RETRIES = 3
BASE_DELAY_MS = 500
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024
DEFAULT_CONCURRENCY = 5


@dataclass
class File:
    file_id: str
    relative_path: str


@dataclass
class FilesApiConfig:
    oauth_token: str
    base_url: Optional[str] = None
    session_id: str = ""


@dataclass
class DownloadResult:
    file_id: str
    path: str
    success: bool
    error: Optional[str] = None
    bytes_written: Optional[int] = None


@dataclass
class UploadResult:
    path: str
    file_id: Optional[str] = None
    size: Optional[int] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class FileMetadata:
    filename: str
    file_id: str
    size: int


def _get_default_api_base_url() -> str:
    return (
        os.environ.get("ANTHROPIC_BASE_URL") or
        os.environ.get("CLAUDE_CODE_API_BASE_URL") or
        "https://api.anthropic.com"
    )


def _log_debug(message: str) -> None:
    print(f"[files-api] {message}", flush=True)


def _log_debug_error(message: str) -> None:
    print(f"[files-api] ERROR: {message}", flush=True)


async def _sleep(ms: float) -> None:
    await asyncio.sleep(ms / 1000)


async def _retry_with_backoff(
    operation: str,
    attempt_fn,
) -> Any:
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
        result = await attempt_fn(attempt)

        if result.get("done"):
            return result.get("value")

        last_error = result.get("error", f"{operation} failed")
        _log_debug(
            f"{operation} attempt {attempt}/{MAX_RETRIES} failed: {last_error}",
        )

        if attempt < MAX_RETRIES:
            delay_ms = BASE_DELAY_MS * (2 ** (attempt - 1))
            _log_debug(f"Retrying {operation} in {delay_ms}ms...")
            await _sleep(delay_ms)

    raise Exception(f"{last_error} after {MAX_RETRIES} attempts")


async def download_file(file_id: str, config: FilesApiConfig) -> bytes:
    base_url = config.base_url or _get_default_api_base_url()
    url = f"{base_url}/v1/files/{file_id}/content"

    headers = {
        "Authorization": f"Bearer {config.oauth_token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": FILES_API_BETA_HEADER,
    }

    _log_debug(f"Downloading file {file_id} from {url}")

    async def attempt(attempt_num: int) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    follow_redirects=True,
                )

            if response.status_code == 200:
                _log_debug(f"Downloaded file {file_id} ({len(response.content)} bytes)")
                return {"done": True, "value": response.content}

            if response.status_code == 404:
                raise Exception(f"File not found: {file_id}")
            if response.status_code == 401:
                raise Exception("Authentication failed: invalid or missing API key")
            if response.status_code == 403:
                raise Exception(f"Access denied to file: {file_id}")

            return {"done": False, "error": f"status {response.status_code}"}
        except httpx.RequestError as e:
            return {"done": False, "error": str(e)}

    return await _retry_with_backoff(f"Download file {file_id}", attempt)


def build_download_path(
    base_path: str,
    session_id: str,
    relative_path: str,
) -> Optional[str]:
    normalized = os.path.normpath(relative_path)
    
    if normalized.startswith(".."):
        _log_debug_error(
            f"Invalid file path: {relative_path}. Path must not traverse above workspace",
        )
        return None

    uploads_base = os.path.join(base_path, session_id, "uploads")
    
    redundant_prefixes = [
        os.path.join(base_path, session_id, "uploads") + os.sep,
        os.sep + "uploads" + os.sep,
    ]
    
    matched_prefix = None
    for prefix in redundant_prefixes:
        if normalized.startswith(prefix):
            matched_prefix = prefix
            break
    
    clean_path = normalized[len(matched_prefix):] if matched_prefix else normalized
    return os.path.join(uploads_base, clean_path)


async def download_and_save_file(
    attachment: File,
    config: FilesApiConfig,
    cwd: Optional[str] = None,
) -> DownloadResult:
    file_id = attachment.file_id
    relative_path = attachment.relative_path
    
    base_path = cwd or os.getcwd()
    full_path = build_download_path(base_path, config.session_id, relative_path)

    if not full_path:
        return DownloadResult(
            file_id=file_id,
            path="",
            success=False,
            error=f"Invalid file path: {relative_path}",
        )

    try:
        content = await download_file(file_id, config)

        parent_dir = os.path.dirname(full_path)
        os.makedirs(parent_dir, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(content)

        _log_debug(f"Saved file {file_id} to {full_path} ({len(content)} bytes)")

        return DownloadResult(
            file_id=file_id,
            path=full_path,
            success=True,
            bytes_written=len(content),
        )
    except Exception as e:
        _log_debug_error(f"Failed to download file {file_id}: {e}")
        return DownloadResult(
            file_id=file_id,
            path=full_path or "",
            success=False,
            error=str(e),
        )


async def _parallel_with_limit(
    items: List,
    fn,
    concurrency: int,
) -> List[Any]:
    results: List[Any] = [None] * len(items)
    current_index = 0

    async def worker():
        nonlocal current_index
        while current_index < len(items):
            index = current_index
            current_index += 1
            item = items[index]
            if item is not None:
                results[index] = await fn(item, index)

    workers = []
    worker_count = min(concurrency, len(items))
    for _ in range(worker_count):
        workers.append(asyncio.create_task(worker()))

    await asyncio.gather(*workers)
    return results


async def download_session_files(
    files: List[File],
    config: FilesApiConfig,
    concurrency: int = DEFAULT_CONCURRENCY,
    cwd: Optional[str] = None,
) -> List[DownloadResult]:
    if not files:
        return []

    _log_debug(
        f"Downloading {len(files)} file(s) for session {config.session_id}",
    )
    start_time = time.time() * 1000

    async def download_one(file_and_idx: Tuple[File, int]) -> DownloadResult:
        file, _ = file_and_idx
        return await download_and_save_file(file, config, cwd)

    files_with_idx = [(f, i) for i, f in enumerate(files)]
    results = await _parallel_with_limit(
        files_with_idx,
        download_one,
        concurrency,
    )

    elapsed_ms = time.time() * 1000 - start_time
    success_count = sum(1 for r in results if r and r.success)
    _log_debug(
        f"Downloaded {success_count}/{len(files)} file(s) in {elapsed_ms}ms",
    )

    return results


async def upload_file(
    file_path: str,
    relative_path: str,
    config: FilesApiConfig,
    signal: Optional[Any] = None,
) -> UploadResult:
    base_url = config.base_url or _get_default_api_base_url()
    url = f"{base_url}/v1/files"

    headers = {
        "Authorization": f"Bearer {config.oauth_token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": FILES_API_BETA_HEADER,
    }

    _log_debug(f"Uploading file {file_path} as {relative_path}")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except Exception as e:
        return UploadResult(
            path=relative_path,
            error=str(e),
            success=False,
        )

    file_size = len(content)

    if file_size > MAX_FILE_SIZE_BYTES:
        return UploadResult(
            path=relative_path,
            error=f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES} bytes (actual: {file_size})",
            success=False,
        )

    boundary = f"----FormBoundary{secrets.token_urlsafe(32)}"
    filename = os.path.basename(relative_path)

    body_parts: List[bytes] = []

    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    body_parts.append(content)
    body_parts.append(b"\r\n")

    body_parts.append(
        f"--{boundary}\r\n"
        "Content-Disposition: form-data; name=\"purpose\"\r\n\r\n"
        "user_data\r\n".encode()
    )

    body_parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(body_parts)

    async def attempt(attempt_num: int) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    content=body,
                    headers={
                        **headers,
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                        "Content-Length": str(len(body)),
                    },
                )

            if response.status_code in (200, 201):
                data = response.json()
                file_id = data.get("id")
                if not file_id:
                    return {"done": False, "error": "Upload succeeded but no file ID returned"}
                _log_debug(f"Uploaded file {file_path} -> {file_id} ({file_size} bytes)")
                return {
                    "done": True,
                    "value": UploadResult(
                        path=relative_path,
                        file_id=file_id,
                        size=file_size,
                        success=True,
                    ),
                }

            if response.status_code == 401:
                raise _UploadNonRetriableError("Authentication failed: invalid or missing API key")
            if response.status_code == 403:
                raise _UploadNonRetriableError("Access denied for upload")
            if response.status_code == 413:
                raise _UploadNonRetriableError("File too large for upload")

            return {"done": False, "error": f"status {response.status_code}"}
        except _UploadNonRetriableError:
            raise
        except httpx.RequestError as e:
            return {"done": False, "error": str(e)}

    try:
        result = await _retry_with_backoff(f"Upload file {relative_path}", attempt)
        return result
    except _UploadNonRetriableError as e:
        return UploadResult(path=relative_path, error=str(e), success=False)
    except Exception as e:
        return UploadResult(path=relative_path, error=str(e), success=False)


class _UploadNonRetriableError(Exception):
    pass


async def upload_session_files(
    files: List[Dict[str, str]],
    config: FilesApiConfig,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> List[UploadResult]:
    if not files:
        return []

    _log_debug(f"Uploading {len(files)} file(s) for session {config.session_id}")
    start_time = time.time() * 1000

    async def upload_one(file_and_idx: Tuple[Dict[str, str], int]) -> UploadResult:
        file, _ = file_and_idx
        return await upload_file(file["path"], file["relative_path"], config)

    files_with_idx = [(f, i) for i, f in enumerate(files)]
    results = await _parallel_with_limit(
        files_with_idx,
        upload_one,
        concurrency,
    )

    elapsed_ms = time.time() * 1000 - start_time
    success_count = sum(1 for r in results if r and r.success)
    _log_debug(f"Uploaded {success_count}/{len(files)} file(s) in {elapsed_ms}ms")

    return results


async def list_files_created_after(
    after_created_at: str,
    config: FilesApiConfig,
) -> List[FileMetadata]:
    base_url = config.base_url or _get_default_api_base_url()
    headers = {
        "Authorization": f"Bearer {config.oauth_token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": FILES_API_BETA_HEADER,
    }

    _log_debug(f"Listing files created after {after_created_at}")

    all_files: List[FileMetadata] = []
    after_id: Optional[str] = None

    while True:
        params: Dict[str, str] = {
            "after_created_at": after_created_at,
        }
        if after_id:
            params["after_id"] = after_id

        async def attempt(attempt_num: int) -> Dict[str, Any]:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(
                        f"{base_url}/v1/files",
                        headers=headers,
                        params=params,
                    )

                if response.status_code == 200:
                    return {"done": True, "value": response.json()}

                if response.status_code == 401:
                    raise Exception("Authentication failed: invalid or missing API key")
                if response.status_code == 403:
                    raise Exception("Access denied to list files")

                return {"done": False, "error": f"status {response.status_code}"}
            except Exception as e:
                if isinstance(e, Exception) and "Authentication" in str(e):
                    raise
                return {"done": False, "error": str(e)}

        try:
            page = await _retry_with_backoff(
                f"List files after {after_created_at}",
                attempt,
            )
        except Exception:
            break

        files = page.get("data", [])
        for f in files:
            all_files.append(FileMetadata(
                filename=f.get("filename", ""),
                file_id=f.get("id", ""),
                size=f.get("size_bytes", 0),
            ))

        if not page.get("has_more"):
            break

        last_file = files[-1] if files else None
        if not last_file or not last_file.get("id"):
            break
        after_id = last_file["id"]

    _log_debug(f"Listed {len(all_files)} files created after {after_created_at}")
    return all_files


def parse_file_specs(file_specs: List[str]) -> List[File]:
    files: List[File] = []

    expanded_specs = []
    for spec in file_specs:
        expanded_specs.extend(spec.split(" "))

    for spec in expanded_specs:
        if not spec:
            continue

        colon_index = spec.find(":")
        if colon_index == -1:
            continue

        file_id = spec[:colon_index]
        relative_path = spec[colon_index + 1:]

        if not file_id or not relative_path:
            _log_debug_error(
                f"Invalid file spec: {spec}. Both file_id and path are required",
            )
            continue

        files.append(File(file_id=file_id, relative_path=relative_path))

    return files
