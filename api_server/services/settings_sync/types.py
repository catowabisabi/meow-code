"""
Settings Sync Types

Type definitions for the user settings sync API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    IDLE = "idle"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(str, Enum):
    """Direction of sync operation."""

    TO_REMOTE = "to_remote"
    FROM_REMOTE = "from_remote"
    BIDIRECTIONAL = "bidirectional"


class SyncTrigger(str, Enum):
    """What triggered the sync operation."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"
    STARTUP = "startup"
    RELOAD = "reload"
    SCHEDULE = "schedule"


class ConflictResolution(str, Enum):
    """How conflicts should be resolved."""

    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    LOCAL_FIRST = "local_first"
    REMOTE_FIRST = "remote_first"
    MERGE = "merge"
    ASK_USER = "ask_user"


class SyncEntry(BaseModel):
    """A single entry in the sync store."""

    key: str
    value: str
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    checksum: Optional[str] = None


class SettingsConflict(BaseModel):
    """Represents a conflict between local and remote settings."""

    key: str
    local_value: str
    remote_value: str
    local_modified: datetime
    remote_modified: datetime
    resolution: ConflictResolution = ConflictResolution.LOCAL_WINS


class SettingsSyncConfig(BaseModel):
    """Configuration for the settings sync service."""

    enabled: bool = False
    sync_interval_seconds: int = 300  # 5 minutes
    max_retries: int = 3
    timeout_ms: int = 10000  # 10 seconds
    max_file_size_bytes: int = 500 * 1024  # 500 KB
    auto_sync: bool = True
    sync_on_startup: bool = True
    conflict_resolution: ConflictResolution = ConflictResolution.LOCAL_WINS
    sync_in_background: bool = True


class UserSyncContent(BaseModel):
    """Content portion of user sync data - flat key-value storage."""

    entries: Dict[str, str] = Field(default_factory=dict)


class UserSyncData(BaseModel):
    """Full response from GET /api/claude_code/user_settings."""

    user_id: str
    version: int
    last_modified: str  # ISO 8601 timestamp
    checksum: str  # MD5 hash
    content: UserSyncContent


class SettingsSyncFetchResult(BaseModel):
    """Result from fetching user settings."""

    success: bool
    data: Optional[UserSyncData] = None
    is_empty: bool = False  # True if 404 (no data exists)
    error: Optional[str] = None
    skip_retry: bool = False


class SettingsSyncUploadResult(BaseModel):
    """Result from uploading user settings."""

    success: bool
    checksum: Optional[str] = None
    last_modified: Optional[str] = None
    error: Optional[str] = None


class SettingsProfile(BaseModel):
    """A settings profile for multi-profile sync support."""

    profile_id: str
    name: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: int
    updated_at: int
    is_active: bool = False


# Sync keys used for different settings files
SYNC_KEYS = {
    "USER_SETTINGS": "~/.claude/settings.json",
    "USER_MEMORY": "~/.claude/CLAUDE.md",
    "PROJECT_SETTINGS": "projects/{project_id}/.claude/settings.local.json",
    "PROJECT_MEMORY": "projects/{project_id}/CLAUDE.local.md",
}


def get_project_settings_key(project_id: str) -> str:
    """Get the sync key for project-specific settings."""
    return SYNC_KEYS["PROJECT_SETTINGS"].format(project_id=project_id)


def get_project_memory_key(project_id: str) -> str:
    """Get the sync key for project-specific memory."""
    return SYNC_KEYS["PROJECT_MEMORY"].format(project_id=project_id)
