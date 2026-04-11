"""
Type definitions for the tips service.

This module provides type definitions for tips including:
- Tip: A single tip with content, cooldown, and relevance logic
- TipContent: The callable content of a tip
- TipContext: Context passed when checking tip relevance
- TipDisplayContext: Context for when a tip is being displayed
"""

from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional, Set, Dict, Any


# Type for tip content - a callable that returns a Promise<string>
TipContent = Callable[[Optional["TipContext"]], Awaitable[str]]

# Type for tip relevance checker - a callable that returns a Promise<boolean>
TipRelevanceChecker = Callable[[Optional["TipContext"]], Awaitable[bool]]


@dataclass
class Tip:
    """
    Represents a single tip that can be shown to the user.
    
    Attributes:
        id: Unique identifier for the tip
        title: Short title for the tip
        content: Async callable that returns the tip text
        category: Category of tip ("shortcut", "feature", "best_practice")
        trigger: What triggers this tip ("first_use", "onboarding", "contextual")
        cooldown_sessions: Number of sessions to wait before showing again
        is_relevant: Async callable that checks if tip should be shown
    """
    id: str
    title: str
    content: TipContent
    category: str = "feature"
    trigger: str = "contextual"
    cooldown_sessions: int = 0
    is_relevant: TipRelevanceChecker = field(default=lambda ctx: True)
    
    @classmethod
    def create(
        cls,
        tip_id: str,
        tip_title: str,
        content_text: str,
        category: str = "feature",
        trigger: str = "contextual",
        cooldown_sessions: int = 0,
        is_relevant: Optional[TipRelevanceChecker] = None,
    ) -> "Tip":
        async def static_content(_ctx: Optional["TipContext"]) -> str:
            return content_text
        
        relevance_fn = is_relevant if is_relevant else (lambda _ctx: True)
        
        return cls(
            id=tip_id,
            title=tip_title,
            content=static_content,
            category=category,
            trigger=trigger,
            cooldown_sessions=cooldown_sessions,
            is_relevant=relevance_fn,
        )


@dataclass
class TipContext:
    """
    Context information passed when checking tip relevance.
    
    This provides tips with information about the current session
    to determine if they are relevant.
    
    Attributes:
        bash_tools: Set of bash tools that have been used
        read_file_state: State of files that have been read
        theme: Theme information for formatting tip content
    """
    bash_tools: Optional[Set[str]] = None
    read_file_state: Optional[Dict[str, Any]] = None
    theme: Optional[Any] = None


@dataclass
class TipDisplayContext:
    """
    Context information for when a tip is being displayed.
    
    Attributes:
        theme: Theme for formatting tip content
        session_number: Current session number
    """
    theme: Optional[Any] = None
    session_number: int = 0


@dataclass
class TipSchedule:
    """
    Represents the schedule for displaying a tip.
    
    Attributes:
        tip_id: ID of the scheduled tip
        scheduled_session: Session number when tip should be shown
        dismissed: Whether the tip has been dismissed
    """
    tip_id: str
    scheduled_session: int
    dismissed: bool = False


@dataclass 
class TipHistoryEntry:
    """
    Represents a single entry in the tip display history.
    
    Attributes:
        tip_id: ID of the tip that was shown
        session_number: Session number when tip was shown
        shown_at: Timestamp when tip was shown
    """
    tip_id: str
    session_number: int
    shown_at: float
