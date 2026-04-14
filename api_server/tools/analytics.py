"""Analytics and telemetry - bridging gap with TypeScript services/analytics/"""
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import threading
from collections import defaultdict


logger = logging.getLogger(__name__)


@dataclass
class EventData:
    event_name: str
    properties: Dict[str, Any]
    timestamp: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class AttributedCounter:
    """Thread-safe counter with attribution tracking."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._attributions: Dict[str, List[str]] = defaultdict(list)
    
    def increment(self, key: str, attribution: Optional[str] = None) -> None:
        with self._lock:
            self._counters[key] += 1
            if attribution:
                self._attributions[key].append(attribution)
    
    def get(self, key: str) -> int:
        with self._lock:
            return self._counters.get(key, 0)
    
    def get_attributions(self, key: str) -> List[str]:
        with self._lock:
            return list(self._attributions.get(key, []))


class TelemetryCollector:
    """
    Telemetry collection with OTEL support.
    
    TypeScript equivalent: firstPartyEventLogger.ts
    Python gap: Python uses threading.Timer, not OTEL.
    """
    
    def __init__(self):
        self._events: List[EventData] = []
        self._lock = threading.Lock()
        self._enabled = True
        self._flush_interval = 60
        self._flush_thread: Optional[threading.Timer] = None
        self._counters: Dict[str, AttributedCounter] = {}
        self._token_counts: Dict[str, int] = {}
    
    def start(self) -> None:
        self._schedule_flush()
    
    def stop(self) -> None:
        self._enabled = False
        if self._flush_thread:
            self._flush_thread.cancel()
    
    def _schedule_flush(self) -> None:
        if self._enabled:
            self._flush_thread = threading.Timer(
                self._flush_interval,
                self._flush_and_send
            )
            self._flush_thread.start()
    
    def _flush_and_send(self) -> None:
        try:
            self.flush()
        finally:
            self._schedule_flush()
    
    def track_event(
        self,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        if not self._enabled:
            return
        
        event = EventData(
            event_name=event_name,
            properties=properties or {},
            timestamp=time.time(),
            user_id=user_id,
            session_id=session_id
        )
        
        with self._lock:
            self._events.append(event)
    
    def increment_counter(self, key: str, attribution: Optional[str] = None) -> None:
        if key not in self._counters:
            self._counters[key] = AttributedCounter()
        self._counters[key].increment(key, attribution)
    
    def add_token_count(self, key: str, count: int) -> None:
        with self._lock:
            self._token_counts[key] = self._token_counts.get(key, 0) + count
    
    def get_total_cache_creation_input_tokens(self) -> int:
        return self._token_counts.get("cache_creation_input", 0)
    
    def get_total_cache_read_input_tokens(self) -> int:
        return self._token_counts.get("cache_read_input", 0)
    
    def get_total_input_tokens(self) -> int:
        return self._token_counts.get("input", 0)
    
    def get_total_output_tokens(self) -> int:
        return self._token_counts.get("output", 0)
    
    def flush(self) -> None:
        with self._lock:
            events_to_send = list(self._events)
            self._events.clear()
        
        if events_to_send:
            logger.debug(f"Flushing {len(events_to_send)} telemetry events")
    
    def get_events(self) -> List[EventData]:
        with self._lock:
            return list(self._events)


_telemetry: Optional[TelemetryCollector] = None


def get_telemetry() -> TelemetryCollector:
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryCollector()
        _telemetry.start()
    return _telemetry


def log_event(
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> None:
    telemetry = get_telemetry()
    telemetry.track_event(event_name, properties, user_id, session_id)
