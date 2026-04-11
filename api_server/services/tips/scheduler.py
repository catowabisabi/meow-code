"""
Tip scheduler for managing tip display timing.

This module provides the TipScheduler class for scheduling tip display,
selecting which tip to show, and managing the tip display lifecycle.
"""

from typing import List, Optional, Callable

from api_server.services.tips.types import Tip, TipContext, TipSchedule
from api_server.services.tips.history import (
    record_tip_shown as record_tip_shown_to_history,
    get_sessions_since_last_shown,
)
from api_server.services.tips.registry import get_relevant_tips


class TipScheduler:
    """
    Schedules and manages tip display.
    
    This class handles selecting which tip to show, scheduling tips,
    dismissing tips, and recording when tips have been shown.
    """
    
    def __init__(self):
        self._scheduled_tips: List[TipSchedule] = []
        self._dismissed_tips: List[str] = []
    
    def schedule_tip(self, tip: Tip, session_number: int) -> None:
        """
        Schedule a tip to be shown at a specific session.
        
        Args:
            tip: The tip to schedule
            session_number: The session number when the tip should be shown
        """
        schedule = TipSchedule(
            tip_id=tip.id,
            scheduled_session=session_number,
            dismissed=False,
        )
        self._scheduled_tips.append(schedule)
    
    def get_next_tip(self, user_id: str, context: dict) -> Optional["Tip"]:
        """
        Get the next tip to show for a user based on context.
        
        Args:
            user_id: The unique identifier of the user
            context: Dictionary containing context information
            
        Returns:
            The next Tip to show, or None if no tip should be shown
        """
        from api_server.services.tips.registry import get_relevant_tips
        from api_server.services.tips.types import TipContext
        
        tip_context = TipContext(
            bash_tools=context.get("bash_tools"),
            read_file_state=context.get("read_file_state"),
            theme=context.get("theme"),
        )
        
        tips = get_relevant_tips.sync(tip_context)
        if not tips:
            return None
        
        return self.select_tip_with_longest_time_since_shown(tips)
    
    def dismiss_tip(self, tip_id: str, user_id: str) -> None:
        """
        Dismiss a tip for a specific user so it won't be shown again.
        
        Args:
            tip_id: The unique identifier of the tip to dismiss
            user_id: The unique identifier of the user dismissing the tip
        """
        for schedule in self._scheduled_tips:
            if schedule.tip_id == tip_id:
                schedule.dismissed = True
        
        dismissed_key = f"{user_id}:{tip_id}"
        if dismissed_key not in self._dismissed_tips:
            self._dismissed_tips.append(dismissed_key)
    
    def reset_tip_schedule(self) -> None:
        """Clear all scheduled and dismissed tips."""
        self._scheduled_tips.clear()
        self._dismissed_tips.clear()
    
    def is_tip_dismissed(self, tip_id: str) -> bool:
        """
        Check if a tip has been dismissed.
        
        Args:
            tip_id: The unique identifier of the tip
            
        Returns:
            True if the tip is dismissed, False otherwise
        """
        if tip_id in self._dismissed_tips:
            return True
        for schedule in self._scheduled_tips:
            if schedule.tip_id == tip_id and schedule.dismissed:
                return True
        return False
    
    def get_scheduled_tips(self) -> List[TipSchedule]:
        """
        Get all scheduled tips.
        
        Returns:
            List of all TipSchedule objects
        """
        return list(self._scheduled_tips)
    
    def select_tip_with_longest_time_since_shown(
        self,
        available_tips: List[Tip],
    ) -> Optional[Tip]:
        """
        Select the tip that hasn't been shown for the longest time.
        
        Args:
            available_tips: List of tips to choose from
            
        Returns:
            The tip that should be shown next, or None if no tips available
        """
        if not available_tips:
            return None
        
        if len(available_tips) == 1:
            return available_tips[0]
        
        tips_with_sessions = [
            (tip, get_sessions_since_last_shown(tip.id))
            for tip in available_tips
        ]
        
        tips_with_sessions.sort(key=lambda x: x[1], reverse=True)
        
        return tips_with_sessions[0][0] if tips_with_sessions else None
    
    async def get_tip_to_show_on_spinner(
        self,
        context: Optional[TipContext] = None,
        tips_enabled: bool = True,
    ) -> Optional[Tip]:
        """
        Get the next tip to show on the spinner.
        
        This considers relevance, cooldown, and selects the tip that
        hasn't been shown for the longest time.
        
        Args:
            context: Optional context for relevance checking
            tips_enabled: Whether tips are enabled (default True)
            
        Returns:
            The tip to show, or None if no tip should be shown
        """
        if not tips_enabled:
            return None
        
        relevant_tips = await get_relevant_tips(context)
        
        if not relevant_tips:
            return None
        
        return self.select_tip_with_longest_time_since_shown(relevant_tips)
    
    def record_shown_tip(
        self,
        tip: Tip,
        log_callback: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        """
        Record that a tip was shown.
        
        This updates the history and optionally logs an event.
        
        Args:
            tip: The tip that was shown
            log_callback: Optional callback for logging analytics
        """
        record_tip_shown_to_history(tip.id)
        
        if log_callback:
            log_callback('tengu_tip_shown', {
                'tipIdLength': len(tip.id),
                'cooldownSessions': tip.cooldown_sessions,
            })


_default_scheduler: Optional[TipScheduler] = None


def get_default_scheduler() -> TipScheduler:
    """Get the default global TipScheduler instance."""
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = TipScheduler()
    return _default_scheduler


def schedule_tip(tip: Tip, session_number: int) -> None:
    """Schedule a tip in the default scheduler."""
    get_default_scheduler().schedule_tip(tip, session_number)


def get_next_tip(user_id: str, context: dict) -> Optional["Tip"]:
    """Get the next tip from the default scheduler."""
    return get_default_scheduler().get_next_tip(user_id, context)


def dismiss_tip(tip_id: str, user_id: str) -> None:
    """Dismiss a tip in the default scheduler."""
    get_default_scheduler().dismiss_tip(tip_id, user_id)


def reset_tip_schedule() -> None:
    """Reset the default scheduler's schedule."""
    get_default_scheduler().reset_tip_schedule()


def select_tip_with_longest_time_since_shown(
    available_tips: List[Tip],
) -> Optional[Tip]:
    """Select the tip with longest time since shown from the default scheduler."""
    return get_default_scheduler().select_tip_with_longest_time_since_shown(available_tips)


async def get_tip_to_show_on_spinner(
    context: Optional[TipContext] = None,
    tips_enabled: bool = True,
) -> Optional[Tip]:
    """Get tip to show on spinner from the default scheduler."""
    return await get_default_scheduler().get_tip_to_show_on_spinner(context, tips_enabled)


def record_shown_tip(
    tip: Tip,
    log_callback: Optional[Callable[[str, dict], None]] = None,
) -> None:
    """Record that a tip was shown in the default scheduler."""
    get_default_scheduler().record_shown_tip(tip, log_callback)
