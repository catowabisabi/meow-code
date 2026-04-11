"""Services package - API server backend services."""

# Core services - these imports should work
from .memory import MemoryService, Memory, MemoryInput, get_memory_index
from .session_store import SessionStore, Session, SessionSummary, Message, generate_title
from .skill import SkillService, Skill, SkillDetail
from .title_gen import generate_smart_title
from .compact import CompactionResult, compact_messages

# Analytics - temporarily using working exports only
try:
    from .analytics import (
        get_feature_value,
        get_dynamic_config,
        refresh_after_auth_change,
        on_growthbook_refresh,
        is_1p_event_logging_enabled,
        log_event_to_1p,
        shutdown_1p_event_logging,
    )
except ImportError:
    pass

# Git service
try:
    from .git_service import (
        GitStatus, get_git_status, get_git_diff, get_git_log,
        git_add, git_commit, git_branch, git_checkout,
    )
except ImportError:
    pass

# Suggestions
try:
    from .suggestions import (
        SuggestionConfig, Suggestion, get_shell_suggestions,
        get_file_suggestions, get_command_suggestions, get_directory_suggestions,
    )
except ImportError:
    pass

# Teleport
try:
    from .teleport import (
        TeleportConfig, check_teleport_available,
        connect_teleport, disconnect_teleport, get_teleport_status,
    )
except ImportError:
    pass

# Diagnostic tracking
try:
    from .diagnostic_tracking import (
        DiagnosticTracker, DiagnosticEvent, ErrorReport,
        get_diagnostic_tracker, track_error, track_performance,
        log_warning, get_recent_diagnostics,
    )
except ImportError:
    pass

# Internal logging
try:
    from .internal_logging import (
        InternalLogger, LogLevel, LogEntry, LoggerConfig,
        get_logger, set_log_level,
    )
except ImportError:
    pass

# Extract memories - NOTE: ExtractMemoriesService doesn't exist, using available classes
try:
    from .extract_memories import (
        MemoryExtractor, ExtractedMemory, ExtractionResult,
        MemoryAnalyzer, MemoryClassifier,
    )
except ImportError:
    pass

# Session memory - NOTE: SessionMemoryService may not exist
try:
    from .session_memory import (
        SessionMemoryCompactor, should_use_session_memory_compaction,
        try_session_memory_compaction,
    )
except ImportError:
    pass

# Tools service - NOTE: ToolsService may not exist
try:
    from .tools_service import ToolsService
except ImportError:
    pass

# Tool use summary
try:
    from .tool_use_summary import (
        ToolUseSummaryReport, generate_tool_use_summary, format_summary_text,
    )
except ImportError:
    pass

# Prompt suggestion
try:
    from .prompt_suggestion import (
        PromptSuggestionService, PromptSuggestion,
    )
except ImportError:
    pass

# Settings sync
try:
    from .settings_sync import SettingsSyncService, SettingsProfile
except ImportError:
    pass

# Policy limits
try:
    from .policy_limits import PolicyLimitsService, PolicyLimit, RateLimitConfig
except ImportError:
    pass

# Remote settings
try:
    from .remote_settings import RemoteSettingsService, RemoteSetting
except ImportError:
    pass

# Tips
try:
    from .tips import TipsService, Tip
except ImportError:
    pass

# Notifier
try:
    from .notifier import NotifierService, Notification
except ImportError:
    pass

# Rate limit messages
try:
    from .rate_limit_messages import RateLimitMessagesService, RateLimitMessage
except ImportError:
    pass

# Token estimation
try:
    from .token_estimation import (
        TokenEstimationService, TokenEstimate, estimate_tokens_for_text,
    )
except ImportError:
    pass

# OAuth
try:
    from .oauth import OAuthService, OAuthProvider, OAuthToken
except ImportError:
    pass

# Team memory sync
try:
    from .team_memory_sync import TeamMemorySyncService, TeamMemory
except ImportError:
    pass

# Auto dream
try:
    from .auto_dream import (
        AutoDreamService, get_auto_dream_service, trigger_manual_dream,
        is_auto_dream_enabled, get_config,
        AutoDreamConfig, DreamTaskState, DreamTurn,
    )
except ImportError:
    pass

# Dream task
try:
    from .auto_dream.dream_task import (
        register_dream_task, complete_dream_task, fail_dream_task,
        get_dream_task, list_dream_tasks,
    )
except ImportError:
    pass

# Agent summary (NEW from Agent 6)
try:
    from .agent_summary import AgentSummaryService, AgentSummary
except ImportError:
    pass

# Magic docs
try:
    from .magic_docs import MagicDocsService, GeneratedDoc
except ImportError:
    pass

# Voice
try:
    from .voice import VoiceService, VoiceInput, VoiceOutput
except ImportError:
    pass

# VCR
try:
    from .vcr import VCRService, VCRSession, ReplayEvent
except ImportError:
    pass

__all__ = [
    # Core
    "MemoryService",
    "Memory",
    "MemoryInput",
    "get_memory_index",
    "SessionStore",
    "Session",
    "SessionSummary",
    "Message",
    "generate_title",
    "SkillService",
    "Skill",
    "SkillDetail",
    "generate_smart_title",
    "CompactionResult",
    "compact_messages",
    # Analytics
    "get_feature_value",
    "get_dynamic_config",
    "refresh_after_auth_change",
    "on_growthbook_refresh",
    "is_1p_event_logging_enabled",
    "log_event_to_1p",
    "shutdown_1p_event_logging",
    # Git
    "GitStatus",
    "get_git_status",
    "get_git_diff",
    "get_git_log",
    "git_add",
    "git_commit",
    "git_branch",
    "git_checkout",
    # Suggestions
    "SuggestionConfig",
    "Suggestion",
    "get_shell_suggestions",
    "get_file_suggestions",
    "get_command_suggestions",
    "get_directory_suggestions",
    # Teleport
    "TeleportConfig",
    "check_teleport_available",
    "connect_teleport",
    "disconnect_teleport",
    "get_teleport_status",
    # Diagnostic
    "DiagnosticTracker",
    "DiagnosticEvent",
    "ErrorReport",
    "get_diagnostic_tracker",
    "track_error",
    "track_performance",
    "log_warning",
    "get_recent_diagnostics",
    # Logging
    "InternalLogger",
    "LogLevel",
    "LogEntry",
    "LoggerConfig",
    "get_logger",
    "set_log_level",
    # Extract memories
    "MemoryExtractor",
    "ExtractedMemory",
    "ExtractionResult",
    "MemoryAnalyzer",
    "MemoryClassifier",
    # Session memory
    "SessionMemoryCompactor",
    "should_use_session_memory_compaction",
    "try_session_memory_compaction",
    # Tools
    "ToolsService",
    # Tool use summary
    "ToolUseSummaryReport",
    "generate_tool_use_summary",
    "format_summary_text",
    # Prompt suggestion
    "PromptSuggestionService",
    "PromptSuggestion",
    # Settings sync
    "SettingsSyncService",
    "SettingsProfile",
    # Policy limits
    "PolicyLimitsService",
    "PolicyLimit",
    "RateLimitConfig",
    # Remote settings
    "RemoteSettingsService",
    "RemoteSetting",
    # Tips
    "TipsService",
    "Tip",
    # Notifier
    "NotifierService",
    "Notification",
    # Rate limit
    "RateLimitMessagesService",
    "RateLimitMessage",
    # Token estimation
    "TokenEstimationService",
    "TokenEstimate",
    "estimate_tokens_for_text",
    # OAuth
    "OAuthService",
    "OAuthProvider",
    "OAuthToken",
    # Team memory
    "TeamMemorySyncService",
    "TeamMemory",
    # Auto dream
    "AutoDreamService",
    "get_auto_dream_service",
    "trigger_manual_dream",
    "is_auto_dream_enabled",
    "get_config",
    "AutoDreamConfig",
    "DreamTaskState",
    "DreamTurn",
    # Dream task
    "register_dream_task",
    "complete_dream_task",
    "fail_dream_task",
    "get_dream_task",
    "list_dream_tasks",
    # Agent summary
    "AgentSummaryService",
    "AgentSummary",
    # Magic docs
    "MagicDocsService",
    "GeneratedDoc",
    # Voice
    "VoiceService",
    "VoiceInput",
    "VoiceOutput",
    # VCR
    "VCRService",
    "VCRSession",
    "ReplayEvent",
]
