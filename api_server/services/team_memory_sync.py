"""
Team Memory Sync Service

Syncs team memory files between the local filesystem and the server API.
Team memory is scoped per-repo (identified by git remote hash) and shared
across all authenticated org members.

This module provides backward compatibility - the actual implementation
is in the team_memory_sync package.
"""

from .team_memory_sync import (
    TeamMemorySyncService as BaseTeamMemorySyncService,
    create_sync_state,
    get_team_memory_context,
    hash_content,
    is_team_memory_sync_available,
    pull_team_memory,
    push_team_memory,
    sync_team_memory,
    sync_from_team_memory,
    sync_to_team_memory,
    TeamMemoryContent,
    TeamMemoryData,
    TeamMemoryEntry,
    PullResult,
    PushResult,
    SyncResult,
    SyncState,
    TeamMemoryConfig,
    TeamMemoryHashesResult,
    TeamMemorySyncFetchResult,
    TeamMemorySyncPushResult,
    TeamMemorySyncUploadResult,
    SecretGuard,
    SecretMatch,
    SecretScanResult,
    SkippedSecretFile,
    WatcherStatus,
    check_forbidden_secrets,
    get_blocked_reasons,
    should_block_memory,
    scan_for_secrets,
    get_secret_label,
    redact_secrets,
    get_sync_settings,
    load_team_memory_config,
    update_sync_settings,
    TeamMemoryWatcher,
    get_watcher_status,
    notify_team_memory_write,
    start_team_memory_watcher,
    stop_team_memory_watcher,
)


TeamMemorySyncService = BaseTeamMemorySyncService
TeamMemory = BaseTeamMemorySyncService


__all__ = [
    "TeamMemorySyncService",
    "TeamMemory",
    "create_sync_state",
    "get_team_memory_context",
    "hash_content",
    "is_team_memory_sync_available",
    "pull_team_memory",
    "push_team_memory",
    "sync_team_memory",
    "sync_from_team_memory",
    "sync_to_team_memory",
    "TeamMemoryContent",
    "TeamMemoryData",
    "TeamMemoryEntry",
    "PullResult",
    "PushResult",
    "SyncResult",
    "SyncState",
    "TeamMemoryConfig",
    "TeamMemoryHashesResult",
    "TeamMemorySyncFetchResult",
    "TeamMemorySyncPushResult",
    "TeamMemorySyncUploadResult",
    "SecretGuard",
    "SecretMatch",
    "SecretScanResult",
    "SkippedSecretFile",
    "WatcherStatus",
    "check_forbidden_secrets",
    "get_blocked_reasons",
    "should_block_memory",
    "scan_for_secrets",
    "get_secret_label",
    "redact_secrets",
    "get_sync_settings",
    "load_team_memory_config",
    "update_sync_settings",
    "TeamMemoryWatcher",
    "get_watcher_status",
    "notify_team_memory_write",
    "start_team_memory_watcher",
    "stop_team_memory_watcher",
]
