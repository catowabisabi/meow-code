"""Team Memory Sync Service - Main sync logic."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .secret_scanner import scan_for_secrets
from .types import (
    PullResult,
    PushResult,
    SkippedSecretFile,
    SyncResult,
    SyncState,
    TeamMemorySyncFetchResult,
    TeamMemorySyncHashesResult,
    TeamMemorySyncUploadResult,
)

logger = logging.getLogger(__name__)


TEAM_MEMORY_SYNC_TIMEOUT_MS = 30_000
MAX_FILE_SIZE_BYTES = 250_000
MAX_PUT_BODY_BYTES = 200_000
MAX_RETRIES = 3
MAX_CONFLICT_RETRIES = 2


def hash_content(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_using_oauth() -> bool:
    return False


def get_team_memory_sync_endpoint(repo_slug: str) -> str:
    base_url = "https://api.claude.ai"
    return f"{base_url}/api/claude_code/team_memory?repo={repo_slug}"


def get_auth_headers() -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    return None, "OAuth not configured"


async def fetch_team_memory_once(
    state: SyncState,
    repo_slug: str,
    etag: Optional[str] = None,
) -> TeamMemorySyncFetchResult:
    try:
        auth_headers, auth_error = get_auth_headers()
        if auth_error:
            return TeamMemorySyncFetchResult(
                success=False,
                error=auth_error,
                skip_retry=True,
                error_type="auth",
            )

        headers: Dict[str, str] = {}
        if auth_headers:
            headers.update(auth_headers)
        if etag:
            headers["If-None-Match"] = f'"{etag}"'

        headers["Content-Type"] = "application/json"

        logger.debug(f"Fetching team memory for repo: {repo_slug}")

        return TeamMemorySyncFetchResult(
            success=True,
            is_empty=True,
        )

    except Exception as e:
        logger.warning(f"Error fetching team memory: {e}")
        return TeamMemorySyncFetchResult(
            success=False,
            error=str(e),
            error_type="unknown",
        )


async def fetch_team_memory_hashes(
    state: SyncState,
    repo_slug: str,
) -> TeamMemorySyncHashesResult:
    try:
        auth_headers, auth_error = get_auth_headers()
        if auth_error:
            return TeamMemorySyncHashesResult(
                success=False,
                error=auth_error,
                error_type="auth",
            )

        logger.debug(f"Fetching team memory hashes for repo: {repo_slug}")

        return TeamMemorySyncHashesResult(
            success=True,
            entry_checksums={},
        )

    except Exception as e:
        logger.warning(f"Error fetching team memory hashes: {e}")
        return TeamMemorySyncHashesResult(
            success=False,
            error=str(e),
            error_type="unknown",
        )


async def upload_team_memory(
    state: SyncState,
    repo_slug: str,
    entries: Dict[str, str],
    if_match_checksum: Optional[str] = None,
) -> TeamMemorySyncUploadResult:
    try:
        auth_headers, auth_error = get_auth_headers()
        if auth_error:
            return TeamMemorySyncUploadResult(
                success=False,
                error=auth_error,
                error_type="auth",
            )

        headers: Dict[str, str] = {}
        if auth_headers:
            headers.update(auth_headers)
        if if_match_checksum:
            headers["If-Match"] = f'"{if_match_checksum}"'

        logger.debug(f"Uploading {len(entries)} entries to team memory")

        return TeamMemorySyncUploadResult(
            success=True,
            checksum=state.last_known_checksum or hash_content(json.dumps(entries)),
        )

    except Exception as e:
        logger.warning(f"Error uploading team memory: {e}")
        return TeamMemorySyncUploadResult(
            success=False,
            error=str(e),
            error_type="unknown",
        )


def batch_delta_by_bytes(
    delta: Dict[str, str],
) -> List[Dict[str, str]]:
    if not delta:
        return []

    EMPTY_BODY_BYTES = len('{"entries":{}}')
    keys = sorted(delta.keys())
    batches: List[Dict[str, str]] = []
    current: Dict[str, str] = {}
    current_bytes = EMPTY_BODY_BYTES

    for key in keys:
        value = delta[key]
        entry_bytes = (
            len(json.dumps(key)) +
            len(json.dumps(value)) +
            2
        )
        if current_bytes + entry_bytes > MAX_PUT_BODY_BYTES and current:
            batches.append(current)
            current = {}
            current_bytes = EMPTY_BODY_BYTES
        current[key] = value
        current_bytes += entry_bytes

    if current:
        batches.append(current)

    return batches


def read_local_team_memory(
    max_entries: Optional[int],
) -> Tuple[Dict[str, str], List[SkippedSecretFile]]:
    entries: Dict[str, str] = {}
    skipped_secrets: List[SkippedSecretFile] = []

    team_dir = Path.home() / ".claude" / "team_memory"
    if not team_dir.exists():
        return entries, skipped_secrets

    try:
        for file_path in team_dir.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    rel_path = str(file_path.relative_to(team_dir))

                    if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
                        logger.info(f"Skipping oversized file: {rel_path}")
                        continue

                    matches = scan_for_secrets(content)
                    if matches:
                        first_match = matches[0]
                        skipped_secrets.append(SkippedSecretFile(
                            path=rel_path,
                            rule_id=first_match.rule_id,
                            label=first_match.label,
                        ))
                        logger.warning(f"Skipping file with secrets: {rel_path}")
                        continue

                    entries[rel_path] = content
                except Exception as e:
                    logger.warning(f"Error reading file {file_path}: {e}")
    except Exception as e:
        logger.warning(f"Error reading team memory directory: {e}")

    keys = sorted(entries.keys())
    if max_entries is not None and len(keys) > max_entries:
        dropped = keys[max_entries:]
        logger.warning(
            f"Local entries {len(keys)} exceeds server cap {max_entries}; "
            f"{len(dropped)} file(s) will NOT sync: {', '.join(dropped)}"
        )
        entries = {k: entries[k] for k in keys[:max_entries]}

    return entries, skipped_secrets


async def write_remote_entries_to_local(
    entries: Dict[str, str],
) -> int:
    team_dir = Path.home() / ".claude" / "team_memory"
    team_dir.mkdir(parents=True, exist_ok=True)

    files_written = 0

    for rel_path, content in entries.items():
        file_path = team_dir / rel_path

        if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            logger.info(f"Skipping oversized remote entry: {rel_path}")
            continue

        try:
            existing = None
            if file_path.exists():
                existing = file_path.read_text(encoding="utf-8")

            if existing == content:
                continue

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            files_written += 1
        except Exception as e:
            logger.warning(f"Failed to write {rel_path}: {e}")

    return files_written


async def pull_team_memory(
    state: SyncState,
    skip_etag_cache: bool = False,
) -> PullResult:
    if not is_using_oauth():
        return PullResult(
            success=False,
            error="OAuth not available",
        )

    repo_slug = "unknown"

    etag = None if skip_etag_cache else state.last_known_checksum
    result = await fetch_team_memory_once(state, repo_slug, etag)

    if not result.success:
        return PullResult(
            success=False,
            error=result.error,
        )

    if result.not_modified:
        return PullResult(
            success=True,
            not_modified=True,
        )

    if result.is_empty or not result.data:
        state.server_checksums.clear()
        return PullResult(success=True)

    entries = result.data.content.entries
    response_checksums = result.data.content.entry_checksums

    state.server_checksums.clear()
    if response_checksums:
        state.server_checksums.update(response_checksums)

    files_written = await write_remote_entries_to_local(entries)

    return PullResult(
        success=True,
        files_written=files_written,
        entry_count=len(entries),
    )


async def push_team_memory(
    state: SyncState,
) -> PushResult:
    if not is_using_oauth():
        return PushResult(
            success=False,
            error="OAuth not available",
            error_type="no_oauth",
        )

    repo_slug = "unknown"

    local_read = read_local_team_memory(state.server_max_entries)
    entries = local_read[0]
    skipped_secrets = local_read[1]

    local_hashes: Dict[str, str] = {}
    for key, content in entries.items():
        local_hashes[key] = hash_content(content)

    for conflict_attempt in range(MAX_CONFLICT_RETRIES + 1):
        delta: Dict[str, str] = {}
        for key, local_hash in local_hashes.items():
            if state.server_checksums.get(key) != local_hash:
                delta[key] = entries[key]

        if not delta:
            return PushResult(
                success=True,
                files_uploaded=0,
                skipped_secrets=skipped_secrets if skipped_secrets else None,
            )

        batches = batch_delta_by_bytes(delta)
        files_uploaded = 0
        last_result: Optional[TeamMemorySyncUploadResult] = None

        for batch in batches:
            result = await upload_team_memory(
                state,
                repo_slug,
                batch,
                state.last_known_checksum,
            )
            last_result = result
            if not result.success:
                break

            for key in batch.keys():
                state.server_checksums[key] = local_hashes[key]
            files_uploaded += len(batch)

        if last_result and last_result.success:
            return PushResult(
                success=True,
                files_uploaded=files_uploaded,
                checksum=last_result.checksum,
                skipped_secrets=skipped_secrets if skipped_secrets else None,
            )

        if last_result and not last_result.conflict:
            if last_result.server_max_entries is not None:
                state.server_max_entries = last_result.server_max_entries
            return PushResult(
                success=False,
                files_uploaded=files_uploaded,
                error=last_result.error,
                error_type=last_result.error_type,
                http_status=last_result.http_status,
            )

        if conflict_attempt >= MAX_CONFLICT_RETRIES:
            return PushResult(
                success=False,
                files_uploaded=0,
                conflict=True,
                error="Conflict resolution failed after retries",
            )

        probe = await fetch_team_memory_hashes(state, repo_slug)
        if not probe.success or not probe.entry_checksums:
            return PushResult(
                success=False,
                files_uploaded=0,
                conflict=True,
                error=f"Conflict resolution hashes probe failed: {probe.error}",
            )

        state.server_checksums.clear()
        state.server_checksums.update(probe.entry_checksums)

    return PushResult(
        success=False,
        files_uploaded=0,
        error="Unexpected end of conflict resolution loop",
    )


async def sync_team_memory(state: SyncState) -> SyncResult:
    pull_result = await pull_team_memory(state, skip_etag_cache=True)

    if not pull_result.success:
        return SyncResult(
            success=False,
            error=pull_result.error,
        )

    push_result = await push_team_memory(state)

    if not push_result.success:
        return SyncResult(
            success=False,
            files_pulled=pull_result.files_written,
            files_pushed=0,
            error=push_result.error,
        )

    return SyncResult(
        success=True,
        files_pulled=pull_result.files_written,
        files_pushed=push_result.files_uploaded,
    )


def is_team_memory_sync_available() -> bool:
    return is_using_oauth()


class TeamMemorySyncService:
    _memories: Dict[str, List[Any]] = {}
    _user_teams: Dict[str, List[str]] = {}

    @classmethod
    def _get_data_dir(cls) -> Path:
        d = Path.home() / ".claude" / "team_memory"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @classmethod
    async def share_memory(
        cls,
        team_id: str,
        user_id: str,
        content: str,
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        now = int(datetime.utcnow().timestamp() * 1000)
        memory = {
            "team_id": team_id,
            "user_id": user_id,
            "content": content,
            "shared_at": now,
            "expires_at": now + ttl_seconds * 1000 if ttl_seconds else None,
        }

        if team_id not in cls._memories:
            cls._memories[team_id] = []
        cls._memories[team_id].append(memory)

        if user_id not in cls._user_teams:
            cls._user_teams[user_id] = []
        if team_id not in cls._user_teams[user_id]:
            cls._user_teams[user_id].append(team_id)

        await cls._persist_team(team_id)
        return memory

    @classmethod
    async def get_team_memories(
        cls,
        team_id: str,
        include_expired: bool = False,
    ) -> List[Any]:
        memories = cls._memories.get(team_id, [])
        now = datetime.utcnow().timestamp() * 1000

        if not include_expired:
            memories = [m for m in memories if not m.get("expires_at") or m["expires_at"] > now]

        return memories

    @classmethod
    async def get_user_shared_memories(cls, user_id: str) -> List[Any]:
        teams = cls._user_teams.get(user_id, [])
        result = []
        for team_id in teams:
            result.extend(await cls.get_team_memories(team_id))
        return result

    @classmethod
    async def delete_memory(cls, team_id: str, memory_idx: int) -> bool:
        if team_id in cls._memories and 0 <= memory_idx < len(cls._memories[team_id]):
            cls._memories[team_id].pop(memory_idx)
            return True
        return False

    @classmethod
    async def clear_team(cls, team_id: str) -> None:
        if team_id in cls._memories:
            cls._memories[team_id] = []

    @classmethod
    async def _persist_team(cls, team_id: str) -> None:
        path = cls._get_data_dir() / f"{team_id}.json"
        memories = cls._memories.get(team_id, [])
        path.write_text(json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    async def load_team(cls, team_id: str) -> None:
        path = cls._get_data_dir() / f"{team_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cls._memories[team_id] = data
            except (json.JSONDecodeError, OSError):
                pass


sync_to_team_memory = push_team_memory
sync_from_team_memory = pull_team_memory


async def get_team_memory_context(team_id: str) -> str:
    memories = await TeamMemorySyncService.get_team_memories(team_id)
    if not memories:
        return ""

    context_parts = []
    for memory in memories:
        content = memory.get("content", "")
        user_id = memory.get("user_id", "unknown")
        shared_at = memory.get("shared_at", 0)
        if shared_at:
            dt = datetime.fromtimestamp(shared_at / 1000)
            context_parts.append(f"[{user_id} at {dt.strftime('%Y-%m-%d %H:%M')}]:\n{content}")
        else:
            context_parts.append(f"[{user_id}]:\n{content}")

    return "\n\n---\n\n".join(context_parts)
