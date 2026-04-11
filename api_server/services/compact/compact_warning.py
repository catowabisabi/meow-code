"""
Compact Warning Hook - React-free subscription to compact warning suppression state.

This module provides a FastAPI-compatible way to subscribe to compact warning
suppression state. It lives in its own file so that the core compact warning
state can remain React-free, allowing it to be imported by non-React code paths.

Ported from the TypeScript compactWarningHook.ts which used useSyncExternalStore.
"""

from typing import Callable, Optional
from dataclasses import dataclass

from .warning_state import (
    CompactWarningState,
    get_warning_state,
    set_warning_state,
    clear_warning_state,
    suppress_compact_warning as _suppress,
    clear_compact_warning_suppression as _clear_suppression,
    use_compact_warning_suppression as _get_suppression,
)


# Default thresholds for warning behavior
DEFAULT_WARNING_THRESHOLD_TOKENS = 150_000
DEFAULT_COMPACT_THRESHOLD_TOKENS = 180_000


@dataclass
class CompactWarningThresholds:
    """Configuration thresholds for compact warnings."""
    warning_threshold: int = DEFAULT_WARNING_THRESHOLD_TOKENS
    compact_threshold: int = DEFAULT_COMPACT_THRESHOLD_TOKENS
    auto_compact_enabled: bool = True


# Global thresholds configuration
_warning_thresholds: CompactWarningThresholds = CompactWarningThresholds()


# Subscribers for state change notifications
_subscribers: list[Callable[[], None]] = []


def _notify_subscribers() -> None:
    """Notify all subscribers of state change."""
    for callback in _subscribers:
        try:
            callback()
        except Exception:
            # Best-effort notification - don't let subscriber errors break the system
            pass


def get_thresholds() -> CompactWarningThresholds:
    """Get the current warning thresholds configuration."""
    return _warning_thresholds


def set_thresholds(thresholds: CompactWarningThresholds) -> None:
    """Set the warning thresholds configuration."""
    global _warning_thresholds
    _warning_thresholds = thresholds
    _notify_subscribers()


def subscribe(callback: Callable[[], None]) -> Callable[[], None]:
    """
    Subscribe to compact warning state changes.
    
    Returns an unsubscribe function.
    """
    _subscribers.append(callback)
    
    def unsubscribe() -> None:
        if callback in _subscribers:
            _subscribers.remove(callback)
    
    return unsubscribe


def get_snapshot() -> bool:
    """
    Get the current snapshot of compact warning suppression state.
    
    This mirrors useSyncExternalStore's getServerSnapshot for React hydration.
    """
    return _get_suppression()


def get_state() -> CompactWarningState:
    """
    Get the full compact warning state.
    
    Returns CompactWarningState with suppressed flag and optional reason.
    """
    return get_warning_state()


def set_state(state: CompactWarningState) -> None:
    """Set the compact warning state."""
    set_warning_state(state)
    _notify_subscribers()


def clear() -> None:
    """Clear compact warning suppression."""
    clear_warning_state()
    _notify_subscribers()


def suppress() -> None:
    """Suppress compact warning."""
    _suppress()
    _notify_subscribers()


def clear_suppression() -> None:
    """Clear compact warning suppression."""
    _clear_suppression()
    _notify_subscribers()


def is_suppressed() -> bool:
    """Check if compact warning is currently suppressed."""
    return _get_suppression()


class CompactWarningHook:
    """
    FastAPI dependency-compatible compact warning hook.
    
    This class provides the same functionality as the React useSyncExternalStore
    hook but adapted for FastAPI dependency injection pattern.
    
    Usage in FastAPI:
    
    ```python
    from fastapi import Depends
    
    def get_compact_warning(
        hook: CompactWarningHook = Depends(CompactWarningHook)
    ) -> bool:
        return hook.get_suppressed()
    ```
    """
    
    def __init__(self):
        self._suppressed: bool = _get_suppression()
        self._thresholds = _warning_thresholds
        self._unsubscribe: Optional[Callable[[], None]] = None
    
    def _on_state_change(self) -> None:
        """Internal callback for state changes."""
        self._suppressed = _get_suppression()
    
    def get_suppressed(self) -> bool:
        """Get current suppression state."""
        return self._suppressed
    
    def get_state(self) -> CompactWarningState:
        """Get full warning state."""
        return get_warning_state()
    
    def get_thresholds(self) -> CompactWarningThresholds:
        """Get warning thresholds."""
        return self._thresholds
    
    def set_thresholds(self, thresholds: CompactWarningThresholds) -> None:
        """Set warning thresholds."""
        self._thresholds = thresholds
        set_thresholds(thresholds)
    
    def suppress(self) -> None:
        """Suppress warning."""
        _suppress()
        self._suppressed = True
    
    def clear_suppression(self) -> None:
        """Clear suppression."""
        _clear_suppression()
        self._suppressed = False
    
    def clear(self) -> None:
        """Clear warning state."""
        clear_warning_state()
        self._suppressed = False
    
    def subscribe(self) -> None:
        """Start subscribing to state changes."""
        if self._unsubscribe is None:
            self._unsubscribe = _subscribers.append(self._on_state_change)
    
    def unsubscribe(self) -> None:
        """Stop subscribing to state changes."""
        if self._unsubscribe is not None:
            try:
                _subscribers.remove(self._on_state_change)
            except ValueError:
                pass
            self._unsubscribe = None
    
    def __enter__(self) -> "CompactWarningHook":
        """Context manager entry."""
        self.subscribe()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.unsubscribe()


def create_compact_warning_hook() -> CompactWarningHook:
    """
    Factory function to create a new CompactWarningHook instance.
    
    This is useful for FastAPI dependency injection:
    
    ```python
    from fastapi import Depends
    
    async def my_endpoint(
        warning_hook: CompactWarningHook = Depends(create_compact_warning_hook)
    ):
        is_suppressed = warning_hook.get_suppressed()
    ```
    """
    return CompactWarningHook()


__all__ = [
    "CompactWarningHook",
    "CompactWarningState",
    "CompactWarningThresholds",
    "create_compact_warning_hook",
    "get_snapshot",
    "get_state",
    "get_thresholds",
    "is_suppressed",
    "set_thresholds",
    "subscribe",
    "suppress",
    "clear_suppression",
    "clear",
]
