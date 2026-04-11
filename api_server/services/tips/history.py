"""
Tip history tracking for the tips service.

This module provides TipHistory class for tracking when tips have been
displayed and determining when they should be shown again.
"""

import time
from typing import Dict, Optional

from api_server.services.tips.types import TipHistoryEntry


class TipHistory:
    """
    Tracks tip display history to enforce cooldown periods.
    
    This class manages the history of displayed tips and provides
    methods to check if a tip should be shown based on its cooldown.
    """
    
    def __init__(self):
        self._history: Dict[str, TipHistoryEntry] = {}
        self._current_session: int = 0
    
    def set_current_session(self, session_number: int) -> None:
        """Set the current session number for history tracking."""
        self._current_session = session_number
    
    def get_current_session(self) -> int:
        """Get the current session number."""
        return self._current_session
    
    def record_tip_shown(self, tip_id: str) -> None:
        """
        Record that a tip was shown to the user.
        
        Args:
            tip_id: The unique identifier of the tip that was shown
        """
        entry = TipHistoryEntry(
            tip_id=tip_id,
            session_number=self._current_session,
            shown_at=time.time(),
        )
        self._history[tip_id] = entry
    
    def should_show_tip(self, tip_id: str, cooldown_sessions: int) -> bool:
        """
        Check if a tip should be shown based on its cooldown.
        
        Args:
            tip_id: The unique identifier of the tip
            cooldown_sessions: Number of sessions to wait before showing again
            
        Returns:
            True if the tip should be shown, False otherwise
        """
        sessions_since_shown = self.get_sessions_since_last_shown(tip_id)
        return sessions_since_shown >= cooldown_sessions
    
    def get_sessions_since_last_shown(self, tip_id: str) -> int:
        """
        Get the number of sessions since a tip was last shown.
        
        Args:
            tip_id: The unique identifier of the tip
            
        Returns:
            Number of sessions since last shown, or infinity if never shown
        """
        entry = self._history.get(tip_id)
        if entry is None:
            return float('inf')
        return self._current_session - entry.session_number
    
    def get_tip_history(self) -> Dict[str, TipHistoryEntry]:
        """
        Get the full tip display history.
        
        Returns:
            Dictionary mapping tip IDs to their history entries
        """
        return dict(self._history)
    
    def reset_tip_history(self) -> None:
        """Clear all tip history."""
        self._history.clear()
    
    def remove_tip(self, tip_id: str) -> None:
        """
        Remove a tip from history.
        
        Args:
            tip_id: The unique identifier of the tip to remove
        """
        self._history.pop(tip_id, None)


_tip_history_instance: Optional[TipHistory] = None


def get_tip_history() -> TipHistory:
    """Get the global TipHistory instance."""
    global _tip_history_instance
    if _tip_history_instance is None:
        _tip_history_instance = TipHistory()
    return _tip_history_instance


def record_tip_shown(tip_id: str) -> None:
    """Record that a tip was shown in the global history."""
    get_tip_history().record_tip_shown(tip_id)


def get_sessions_since_last_shown(tip_id: str) -> int:
    """Get sessions since a tip was last shown from global history."""
    return get_tip_history().get_sessions_since_last_shown(tip_id)


def should_show_tip(tip_id: str, cooldown_sessions: int) -> bool:
    """Check if a tip should be shown based on cooldown from global history."""
    return get_tip_history().should_show_tip(tip_id, cooldown_sessions)
