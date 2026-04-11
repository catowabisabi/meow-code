"""
Tips service package.

This package provides the tips service functionality for displaying
helpful tips to users during their sessions.

Modules:
    types: Type definitions for tips
    history: Tip display history tracking
    registry: Tip registry for managing tip definitions
    scheduler: Tip scheduler for managing tip display

Classes:
    Tip: A single tip with content and relevance logic
    TipContext: Context for relevance checking
    TipDisplayContext: Context for tip display
    TipSchedule: Schedule information for a tip
    TipHistoryEntry: An entry in the tip history
    TipHistory: Tracks tip display history
    TipRegistry: Manages tip definitions
    TipScheduler: Schedules and manages tip display

Functions:
    get_tip_history: Get global tip history instance
    record_tip_shown: Record a tip was shown
    get_sessions_since_last_shown: Get sessions since tip was shown
    should_show_tip: Check if tip should be shown
    get_default_registry: Get global registry instance
    register_tip: Register a tip in default registry
    get_tip: Get a tip by ID
    list_tips: List all tips
    get_random_tip: Get a random tip
    get_relevant_tips: Get relevant tips
    get_default_scheduler: Get global scheduler instance
    schedule_tip: Schedule a tip
    get_next_tip: Get next scheduled tip
    dismiss_tip: Dismiss a tip
    reset_tip_schedule: Reset tip schedule
    select_tip_with_longest_time_since_shown: Select tip by history
    get_tip_to_show_on_spinner: Get tip for spinner display
    record_shown_tip: Record tip was shown
"""

from api_server.services.tips.types import (
    Tip,
    TipContent,
    TipContext,
    TipDisplayContext,
    TipSchedule,
    TipHistoryEntry,
    TipRelevanceChecker,
)

from api_server.services.tips.history import (
    TipHistory,
    get_tip_history,
    record_tip_shown,
    get_sessions_since_last_shown,
    should_show_tip,
)

from api_server.services.tips.registry import (
    TipRegistry,
    get_default_registry,
    register_tip,
    get_tip,
    list_tips,
    get_random_tip,
    get_relevant_tips,
)

from api_server.services.tips.scheduler import (
    TipScheduler,
    get_default_scheduler,
    schedule_tip,
    get_next_tip,
    dismiss_tip,
    reset_tip_schedule,
    select_tip_with_longest_time_since_shown,
    get_tip_to_show_on_spinner,
    record_shown_tip,
)

__all__ = [
    "Tip",
    "TipContent",
    "TipContext",
    "TipDisplayContext", 
    "TipSchedule",
    "TipHistoryEntry",
    "TipRelevanceChecker",
    "TipHistory",
    "get_tip_history",
    "record_tip_shown",
    "get_sessions_since_last_shown",
    "should_show_tip",
    "TipRegistry",
    "get_default_registry",
    "register_tip",
    "get_tip",
    "list_tips",
    "get_random_tip",
    "get_relevant_tips",
    "TipScheduler",
    "get_default_scheduler",
    "schedule_tip",
    "get_next_tip",
    "dismiss_tip",
    "reset_tip_schedule",
    "select_tip_with_longest_time_since_shown",
    "get_tip_to_show_on_spinner",
    "record_shown_tip",
]
