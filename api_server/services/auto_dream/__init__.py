"""
Auto Dream memory consolidation system.

This module provides background memory consolidation that fires a forked
subagent to synthesize memories from recent sessions.

Public APIs:
- AutoDreamService: Main service class
- get_auto_dream_service(): Get the global service instance
- trigger_manual_dream(): Trigger manual /dream consolidation
- is_auto_dream_enabled(): Check if feature is enabled
- get_config(): Get feature configuration
"""
from .auto_dream import (
    AutoDreamService,
    get_auto_dream_service,
    trigger_manual_dream,
)
from .config import get_config, is_auto_dream_enabled
from .consolidation_lock import (
    list_sessions_touched_since_async,
    read_last_consolidated_at_async,
    record_consolidation_async,
    rollback_consolidation_lock_async,
    try_acquire_consolidation_lock_async,
)
from .dream_task import (
    add_dream_turn,
    cleanup_completed_tasks,
    complete_dream_task,
    fail_dream_task,
    get_dream_task,
    get_running_dream_tasks,
    is_dream_task,
    kill_dream_task,
    list_dream_tasks,
    register_dream_task,
)
from .types import (
    AutoDreamConfig,
    CacheSafeParams,
    DreamConsolidationResult,
    DreamTaskState,
    DreamTurn,
    ForkAgentResult,
    REPLHookContext,
    ToolPermission,
)

__all__ = [
    "AutoDreamService",
    "get_auto_dream_service",
    "trigger_manual_dream",
    "is_auto_dream_enabled",
    "get_config",
    "list_sessions_touched_since_async",
    "read_last_consolidated_at_async",
    "record_consolidation_async",
    "rollback_consolidation_lock_async",
    "try_acquire_consolidation_lock_async",
    "add_dream_turn",
    "cleanup_completed_tasks",
    "complete_dream_task",
    "fail_dream_task",
    "get_dream_task",
    "get_running_dream_tasks",
    "is_dream_task",
    "kill_dream_task",
    "list_dream_tasks",
    "register_dream_task",
    "AutoDreamConfig",
    "CacheSafeParams",
    "DreamConsolidationResult",
    "DreamTaskState",
    "DreamTurn",
    "ForkAgentResult",
    "REPLHookContext",
    "ToolPermission",
]
