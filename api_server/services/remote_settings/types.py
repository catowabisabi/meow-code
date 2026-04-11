"""
Type definitions for remote settings service.

Based on TypeScript types.ts and related files from:
_claude_code_leaked_source_code/src/services/remoteManagedSettings/
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SettingsSource(str, Enum):
    """Source of the settings value."""
    LOCAL = "local"
    REMOTE = "remote"
    MDM = "mdm"
    POLICY = "policy"
    DEFAULT = "default"


class SettingsSyncStatus(str, Enum):
    """Status of settings synchronization."""
    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    CACHE_VALID = "cache_valid"
    NOT_MODIFIED = "not_modified"


class RemoteSettingEntry(BaseModel):
    """A single remote setting entry."""
    key: str
    value: Any
    updated_at: int = Field(description="Unix timestamp in milliseconds")
    source: str
    is_override: bool = False
    checksum: Optional[str] = None

    class Config:
        frozen = False


class RemoteSettingsConfig(BaseModel):
    """Configuration for remote settings service."""
    remote_url: Optional[str] = None
    enabled: bool = True
    poll_interval_ms: int = Field(default=60 * 60 * 1000, description="1 hour default")
    timeout_ms: int = Field(default=10000, description="10 seconds default")
    max_retries: int = Field(default=5)
    cache_ttl_seconds: int = Field(default=3600, description="1 hour default")
    use_etag: bool = True
    fail_open: bool = True

    class Config:
        frozen = False


class RemoteManagedSettingsResponse(BaseModel):
    """Response schema for remote managed settings API."""
    uuid: str = Field(description="Settings UUID")
    checksum: str = Field(description="Settings checksum for caching")
    settings: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False


class RemoteManagedSettingsFetchResult(BaseModel):
    """Result of fetching remotely managed settings."""
    success: bool
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Settings dict, or None means 304 Not Modified (cache valid)"
    )
    checksum: Optional[str] = None
    error: Optional[str] = None
    skip_retry: bool = Field(
        default=False,
        description="If true, don't retry on failure (e.g., auth errors)"
    )

    class Config:
        frozen = False


class SettingMetadata(BaseModel):
    """Metadata for a single setting."""
    key: str
    source: SettingsSource
    updated_at: int = Field(description="Unix timestamp in milliseconds")
    is_managed: bool = False
    is_encrypted: bool = False
    description: Optional[str] = None
    allowed_values: Optional[List[Any]] = None

    class Config:
        frozen = False


class RemotePolicy(BaseModel):
    """Remote policy for settings enforcement."""
    policy_id: str
    policy_name: str
    enforced_keys: List[str] = Field(default_factory=list)
    blocked_keys: List[str] = Field(default_factory=list)
    required_keys: List[str] = Field(default_factory=list)
    default_values: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    version: int = 1
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

    class Config:
        frozen = False


class PolicyViolation(BaseModel):
    """A policy violation detected."""
    key: str
    violation_type: str = Field(description="Type: 'required', 'blocked', 'enforced', 'invalid_value'")
    message: str
    severity: str = Field(default="error", description="'error', 'warning', 'info'")
    current_value: Optional[Any] = None
    expected_value: Optional[Any] = None

    class Config:
        frozen = False


class MergeStrategy(str, Enum):
    """Strategy for merging remote and local settings."""
    REMOTE_WINS = "remote_wins"
    LOCAL_WINS = "local_wins"
    REMOTE_ONLY = "remote_only"
    LOCAL_ONLY = "local_only"
    SMART_MERGE = "smart_merge"


class SettingsCacheEntry(BaseModel):
    """A cached settings entry with metadata."""
    key: str
    value: Any
    checksum: str
    cached_at: int = Field(description="Unix timestamp in milliseconds")
    expires_at: Optional[int] = Field(description="Unix timestamp in milliseconds")
    source: SettingsSource = SettingsSource.REMOTE

    class Config:
        frozen = False


class EligibilityStatus(BaseModel):
    """Status of remote managed settings eligibility."""
    eligible: bool
    reason: Optional[str] = None
    provider: Optional[str] = None
    subscription_type: Optional[str] = None
    auth_type: Optional[str] = None


class SecurityCheckResult(BaseModel):
    """Result of security check for settings changes."""
    passed: bool
    violations: List[PolicyViolation] = Field(default_factory=list)
    message: Optional[str] = None
    requires_confirmation: bool = False


class PollingState(BaseModel):
    """State of background polling."""
    is_running: bool = False
    interval_id: Optional[str] = None
    last_poll_at: Optional[int] = None
    poll_count: int = 0
    consecutive_failures: int = 0

    class Config:
        frozen = False
