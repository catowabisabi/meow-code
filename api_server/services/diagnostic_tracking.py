"""Diagnostic Tracking Service.
Captures errors, warnings, and performance metrics for debugging and monitoring.
"""
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
from pathlib import Path


@dataclass
class DiagnosticEvent:
    """A diagnostic event to track."""
    event_type: str  # "error", "warning", "performance", "info"
    timestamp: float
    message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None


@dataclass 
class ErrorReport:
    """An error report with context."""
    error_type: str
    message: str
    timestamp: float
    stack_trace: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class DiagnosticTracker:
    """Tracks diagnostic events and errors."""
    
    _instance: Optional["DiagnosticTracker"] = None
    _events: List[DiagnosticEvent] = []
    _max_events: int = 1000
    
    def __new__(cls) -> "DiagnosticTracker":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def track_event(
        self,
        event_type: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Track a diagnostic event."""
        event = DiagnosticEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().timestamp(),
            message=message,
            context=context or {},
            duration_ms=duration_ms,
        )
        self._events.append(event)
        
        # Keep only recent events
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def track_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ErrorReport:
        """Track an error with full context."""
        report = ErrorReport(
            error_type=type(error).__name__,
            message=str(error),
            timestamp=datetime.utcnow().timestamp(),
            stack_trace=traceback.format_exc(),
            session_id=session_id,
            user_id=user_id,
            context=context or {},
        )
        
        event = DiagnosticEvent(
            event_type="error",
            timestamp=report.timestamp,
            message=f"{report.error_type}: {report.message}",
            stack_trace=report.stack_trace,
            context=context or {},
        )
        self._events.append(event)
        
        return report
    
    def track_performance(
        self,
        operation: str,
        duration_ms: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track a performance metric."""
        self.track_event(
            event_type="performance",
            message=f"{operation}: {duration_ms}ms",
            context={"operation": operation, "duration_ms": duration_ms, **(context or {})},
            duration_ms=duration_ms,
        )
    
    def get_recent_events(self, limit: int = 100) -> List[DiagnosticEvent]:
        """Get recent diagnostic events."""
        return self._events[-limit:]
    
    def get_errors(self, limit: int = 50) -> List[DiagnosticEvent]:
        """Get recent error events."""
        return [e for e in self._events if e.event_type == "error"][-limit:]
    
    def get_performance_metrics(self, limit: int = 100) -> List[DiagnosticEvent]:
        """Get recent performance events."""
        return [e for e in self._events if e.event_type == "performance"][-limit:]
    
    def clear_events(self) -> None:
        """Clear all tracked events."""
        self._events.clear()
    
    def export_events(self, file_path: Optional[Path] = None) -> str:
        """Export events to JSON format."""
        data = [
            {
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "message": e.message,
                "stack_trace": e.stack_trace,
                "context": e.context,
                "duration_ms": e.duration_ms,
            }
            for e in self._events
        ]
        
        json_str = json.dumps(data, indent=2)
        
        if file_path:
            file_path.write_text(json_str, encoding="utf-8")
        
        return json_str


# Global tracker instance
_tracker: Optional[DiagnosticTracker] = None


def get_diagnostic_tracker() -> DiagnosticTracker:
    """Get the global diagnostic tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = DiagnosticTracker()
    return _tracker


async def track_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ErrorReport:
    """Convenience function to track an error."""
    return get_diagnostic_tracker().track_error(error, context, session_id, user_id)


async def track_performance(
    operation: str,
    duration_ms: float,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience function to track performance."""
    get_diagnostic_tracker().track_performance(operation, duration_ms, context)


async def log_warning(
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience function to log a warning."""
    get_diagnostic_tracker().track_event("warning", message, context)


async def get_recent_diagnostics(limit: int = 100) -> List[DiagnosticEvent]:
    """Get recent diagnostic events."""
    return get_diagnostic_tracker().get_recent_events(limit)