"""Settings watchdog for monitoring and notifying about changes."""

import threading
import time
from typing import Any, Callable, Dict, List, Optional


class SettingsWatchdog:
    _instance: Optional["SettingsWatchdog"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "SettingsWatchdog":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._watching = False
        self._interval_id: Optional[str] = None
        self._listeners: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._last_notified: Dict[str, int] = {}
        self._poll_interval_ms = 60 * 60 * 1000
        self._timer: Optional[threading.Timer] = None

    @classmethod
    def get_instance(cls) -> "SettingsWatchdog":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_watching(self, poll_interval_ms: Optional[int] = None) -> None:
        with self._lock:
            if self._watching:
                return

            if poll_interval_ms is not None:
                self._poll_interval_ms = poll_interval_ms

            self._watching = True
            self._schedule_next_poll()

    def stop_watching(self) -> None:
        with self._lock:
            self._watching = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _schedule_next_poll(self) -> None:
        if not self._watching:
            return

        interval_seconds = self._poll_interval_ms / 1000.0
        self._timer = threading.Timer(interval_seconds, self._poll_callback)
        self._timer.daemon = True
        self._timer.start()

    def _poll_callback(self) -> None:
        if not self._watching:
            return

        try:
            self._check_for_changes()
        finally:
            self._schedule_next_poll()

    def _check_for_changes(self) -> None:
        pass

    def on_settings_changed(
        self,
        namespace: str,
        callback: Callable[[str, Any, Any], None],
    ) -> Callable[[], None]:
        if namespace not in self._listeners:
            self._listeners[namespace] = []

        self._listeners[namespace].append(callback)

        def unsubscribe() -> None:
            if namespace in self._listeners:
                if callback in self._listeners[namespace]:
                    self._listeners[namespace].remove(callback)

        return unsubscribe

    def notify_change(
        self,
        namespace: str,
        old_value: Any = None,
        new_value: Any = None,
    ) -> None:
        now = int(time.time() * 1000)
        self._last_notified[namespace] = now

        if namespace in self._listeners:
            for callback in self._listeners[namespace]:
                try:
                    callback(namespace, old_value, new_value)
                except Exception:
                    pass

    def notify_changes(self, changes: Dict[str, tuple[Any, Any]]) -> None:
        for namespace, (old_value, new_value) in changes.items():
            self.notify_change(namespace, old_value, new_value)

    def get_last_notification_time(self, namespace: str) -> Optional[int]:
        return self._last_notified.get(namespace)

    def is_watching(self) -> bool:
        return self._watching

    def get_poll_interval(self) -> int:
        return self._poll_interval_ms

    def set_poll_interval(self, interval_ms: int) -> None:
        self._poll_interval_ms = interval_ms

    def add_listener(
        self,
        namespace: str,
        callback: Callable[[str, Any, Any], None],
    ) -> None:
        if namespace not in self._listeners:
            self._listeners[namespace] = []
        if callback not in self._listeners[namespace]:
            self._listeners[namespace].append(callback)

    def remove_listener(
        self,
        namespace: str,
        callback: Callable[[str, Any, Any], None],
    ) -> bool:
        if namespace in self._listeners:
            if callback in self._listeners[namespace]:
                self._listeners[namespace].remove(callback)
                return True
        return False

    def clear_listeners(self, namespace: Optional[str] = None) -> None:
        if namespace is None:
            self._listeners.clear()
        elif namespace in self._listeners:
            del self._listeners[namespace]

    def get_listener_count(self, namespace: Optional[str] = None) -> int:
        if namespace is not None:
            return len(self._listeners.get(namespace, []))
        return sum(len(listeners) for listeners in self._listeners.values())
