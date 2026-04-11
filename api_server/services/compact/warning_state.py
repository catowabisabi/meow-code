"""Compact warning state management - tracks whether warning should be suppressed."""
from .types import CompactWarningState


_suppressed = False


def get_warning_state() -> CompactWarningState:
    return CompactWarningState(suppressed=_suppressed)


def set_warning_state(state: CompactWarningState) -> None:
    global _suppressed
    _suppressed = state.suppressed


def clear_warning_state() -> None:
    global _suppressed
    _suppressed = False


def suppress_compact_warning() -> None:
    global _suppressed
    _suppressed = True


def clear_compact_warning_suppression() -> None:
    global _suppressed
    _suppressed = False


class CompactWarningStateManager:
    def __init__(self):
        self._suppressed = False
    
    def get_state(self) -> CompactWarningState:
        return CompactWarningState(suppressed=self._suppressed)
    
    def set_state(self, state: CompactWarningState) -> None:
        self._suppressed = state.suppressed
    
    def clear(self) -> None:
        self._suppressed = False
    
    def suppress(self) -> None:
        self._suppressed = True
    
    def is_suppressed(self) -> bool:
        return self._suppressed


def use_compact_warning_suppression() -> bool:
    return _suppressed