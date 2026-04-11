"""
Team Memory Sync Types

Type definitions for the repo-scoped team memory sync API.
Based on the backend API contract from anthropic/anthropic#250711.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─── Core Data Types ──────────────────────────────────────────


@dataclass
class TeamMemoryContent:
    """Content portion of team memory data - flat key-value storage."""
    entries: Dict[str, str] = field(default_factory=dict)
    entry_checksums: Optional[Dict[str, str]] = None


@dataclass
class TeamMemoryData:
    """Full response from GET /api/claude_code/team_memory"""
    organization_id: str
    repo: str
    version: int
    last_modified: str  # ISO 8601 timestamp
    checksum: str  # SHA256 with 'sha256:' prefix
    content: TeamMemoryContent


@dataclass
class SkippedSecretFile:
    """A file skipped during push because it contains a detected secret."""
    path: str  # Relative to the team memory directory
    rule_id: str  # Gitleaks rule ID (e.g., "github-pat", "aws-access-token")
    label: str  # Human-readable label derived from rule ID


# ─── Sync State ──────────────────────────────────────────────


@dataclass
class SyncState:
    """Mutable state for the team memory sync service."""
    last_known_checksum: Optional[str] = None
    server_checksums: Dict[str, str] = field(default_factory=dict)
    server_max_entries: Optional[int] = None


def create_sync_state() -> SyncState:
    """Create a new SyncState instance."""
    return SyncState(
        last_known_checksum=None,
        server_checksums={},
        server_max_entries=None,
    )


# ─── Result Types ────────────────────────────────────────────


@dataclass
class TeamMemorySyncFetchResult:
    """Result from fetching team memory"""
    success: bool
    data: Optional[TeamMemoryData] = None
    is_empty: bool = False  # true if 404 (no data exists)
    not_modified: bool = False  # true if 304 (ETag matched)
    checksum: Optional[str] = None  # ETag from response header
    error: Optional[str] = None
    skip_retry: bool = False
    error_type: Optional[str] = None  # 'auth' | 'timeout' | 'network' | 'parse' | 'unknown'
    http_status: Optional[int] = None


@dataclass
class TeamMemoryHashesResult:
    """Lightweight metadata-only probe result (GET ?view=hashes)."""
    success: bool
    version: Optional[int] = None
    checksum: Optional[str] = None
    entry_checksums: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None  # 'auth' | 'timeout' | 'network' | 'parse' | 'unknown'
    http_status: Optional[int] = None


@dataclass
class TeamMemorySyncPushResult:
    """Result from uploading team memory with conflict info"""
    success: bool
    files_uploaded: int = 0
    checksum: Optional[str] = None
    conflict: bool = False  # true if 412 Precondition Failed
    error: Optional[str] = None
    skipped_secrets: Optional[List[SkippedSecretFile]] = None
    error_type: Optional[str] = None  # 'auth' | 'timeout' | 'network' | 'conflict' | 'unknown' | 'no_oauth' | 'no_repo'
    http_status: Optional[int] = None


@dataclass
class TeamMemorySyncUploadResult:
    """Result from uploading team memory"""
    success: bool
    checksum: Optional[str] = None
    last_modified: Optional[str] = None
    conflict: bool = False  # true if 412 Precondition Failed
    error: Optional[str] = None
    error_type: Optional[str] = None  # 'auth' | 'timeout' | 'network' | 'unknown'
    http_status: Optional[int] = None
    server_error_code: Optional[str] = None  # 'team_memory_too_many_entries'
    server_max_entries: Optional[int] = None
    server_received_entries: Optional[int] = None


# ─── Pull/Push Return Types ───────────────────────────────────


@dataclass
class PullResult:
    """Result from pullTeamMemory"""
    success: bool
    files_written: int = 0
    entry_count: int = 0
    not_modified: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class PushResult:
    """Result from pushTeamMemory (extends PushResult with conflict info)"""
    success: bool
    files_uploaded: int = 0
    checksum: Optional[str] = None
    conflict: bool = False
    error: Optional[str] = None
    skipped_secrets: Optional[List[SkippedSecretFile]] = None
    error_type: Optional[str] = None
    http_status: Optional[int] = None


@dataclass
class SyncResult:
    """Result from syncTeamMemory"""
    success: bool
    files_pulled: int = 0
    files_pushed: int = 0
    error: Optional[str] = None


# ─── Secret Scanner Types ─────────────────────────────────────


@dataclass
class SecretMatch:
    """A secret detected in content"""
    rule_id: str  # Gitleaks rule ID (e.g., "github-pat", "aws-access-token")
    label: str  # Human-readable label derived from the rule ID


@dataclass
class SecretScanResult:
    """Result from scanning content for secrets"""
    matches: List[SecretMatch] = field(default_factory=list)
    has_secrets: bool = False

    @classmethod
    def from_matches(cls, matches: List[SecretMatch]) -> "SecretScanResult":
        return cls(matches=matches, has_secrets=len(matches) > 0)


# ─── Secret Guard Types ───────────────────────────────────────


@dataclass
class SecretGuardConfig:
    """Configuration for secret guard"""
    enabled: bool = True
    block_on_secret: bool = True


@dataclass
class WatcherEvent:
    """Event from the file watcher"""
    event_type: str  # 'add' | 'change' | 'unlink'
    path: str
    is_directory: bool = False


@dataclass
class WatcherStatus:
    """Status of the file watcher"""
    is_watching: bool = False
    push_in_progress: bool = False
    has_pending_changes: bool = False
    push_suppressed: bool = False
    suppress_reason: Optional[str] = None


# ─── Team Memory Entry ────────────────────────────────────────


@dataclass
class TeamMemoryEntry:
    """A single team memory entry"""
    team_id: str
    user_id: str
    content: str
    shared_at: int  # Unix timestamp in milliseconds
    expires_at: Optional[int] = None  # Unix timestamp in milliseconds


@dataclass
class TeamMemoryConfig:
    """Configuration for team memory sync"""
    sync_enabled: bool = True
    sync_timeout_ms: int = 30_000
    max_file_size_bytes: int = 250_000
    max_put_body_bytes: int = 200_000
    max_retries: int = 3
    max_conflict_retries: int = 2
    debounce_ms: int = 2000
