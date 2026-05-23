"""
CircuitBreakerService - Provider-specific circuit breakers for LLM request resilience.

States:
  - CLOSED: Normal operation, requests pass through
  - OPEN: Provider failing, requests skip to next provider
  - HALF_OPEN: Testing if provider recovered

Transitions:
  - CLOSED → OPEN: 5 failures within 60 seconds
  - OPEN → HALF_OPEN: after 30 seconds recovery timeout
  - HALF_OPEN → CLOSED: on success
  - HALF_OPEN → OPEN: on failure
"""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Any, Optional, Dict

FAILURE_THRESHOLD = 5
FAILURE_WINDOW_SECONDS = 60
RECOVERY_TIMEOUT_SECONDS = 30


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = FAILURE_THRESHOLD
    failure_window_seconds: int = FAILURE_WINDOW_SECONDS
    recovery_timeout_seconds: int = RECOVERY_TIMEOUT_SECONDS


@dataclass
class CircuitStatus:
    provider: str
    state: CircuitState
    failure_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    last_failure_reason: Optional[str]


@dataclass
class CircuitBreaker:
    provider: str
    config: CircuitBreakerConfig
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _failure_window_start: Optional[float] = None
    _last_failure_time: Optional[float] = None
    _last_success_time: Optional[float] = None
    _last_failure_reason: Optional[str] = None
    _recovery_timer: Optional["asyncio.Task"] = None
    # Heartbeat data structures
    latency_samples: list = field(default_factory=list)
    circuit_state_history: list = field(default_factory=list)
    failure_timestamps: list = field(default_factory=list)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def last_failure_time(self) -> Optional[float]:
        return self._last_failure_time

    @property
    def last_failure_reason(self) -> Optional[str]:
        return self._last_failure_reason

    @property
    def last_success_time(self) -> Optional[float]:
        return self._last_success_time

    def _reset_window(self) -> None:
        self._failure_window_start = time.time()
        self._failure_count = 0

    def _record_failure(self, reason: str = "") -> None:
        now = time.time()
        if self._failure_window_start is None:
            self._reset_window()
        elif now - self._failure_window_start > self.config.failure_window_seconds:
            self._reset_window()
        self._failure_count += 1
        self._last_failure_time = now
        self._last_failure_reason = reason
        # Record failure timestamp for heartbeat
        self.failure_timestamps.append(now)
        # Trim to last 24h
        cutoff = now - 86400
        self.failure_timestamps = [t for t in self.failure_timestamps if t > cutoff]
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self.config.failure_threshold
        ):
            self._transition_to_open()

    def _record_success(self) -> None:
        self._last_success_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to_closed()

    def _transition_to_open(self) -> None:
        now = time.time()
        self.circuit_state_history.append({"timestamp": now, "from_state": self._state.value, "to_state": CircuitState.OPEN.value})
        self._state = CircuitState.OPEN
        self._start_recovery_timer()

    def _transition_to_closed(self) -> None:
        now = time.time()
        self.circuit_state_history.append({"timestamp": now, "from_state": self._state.value, "to_state": CircuitState.CLOSED.value})
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_window_start = None
        if self._recovery_timer:
            self._recovery_timer.cancel()
            self._recovery_timer = None

    def _transition_to_half_open(self) -> None:
        now = time.time()
        self.circuit_state_history.append({"timestamp": now, "from_state": self._state.value, "to_state": CircuitState.HALF_OPEN.value})
        self._state = CircuitState.HALF_OPEN

    def _start_recovery_timer(self) -> None:
        async def _timer():
            await asyncio.sleep(self.config.recovery_timeout_seconds)
            if self._state == CircuitState.OPEN:
                self._transition_to_half_open()

        self._recovery_timer = asyncio.create_task(_timer())

    def force_open(self) -> None:
        self.circuit_state_history.append({"timestamp": time.time(), "from_state": self._state.value, "to_state": CircuitState.OPEN.value})
        self._state = CircuitState.OPEN
        self._failure_count = self.config.failure_threshold
        self._start_recovery_timer()

    def reset(self) -> None:
        self.circuit_state_history.append({"timestamp": time.time(), "from_state": self._state.value, "to_state": CircuitState.CLOSED.value})
        self._transition_to_closed()
        self._last_failure_time = None
        self._last_failure_reason = None

    def get_status(self) -> CircuitStatus:
        return CircuitStatus(
            provider=self.provider,
            state=self._state,
            failure_count=self._failure_count,
            last_failure_time=self._last_failure_time,
            last_success_time=self._last_success_time,
            last_failure_reason=self._last_failure_reason,
        )


class CircuitBreakerService:
    _instance: Optional["CircuitBreakerService"] = None

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._config = config or CircuitBreakerConfig()

    @classmethod
    def get_instance(cls) -> "CircuitBreakerService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_breaker(self, provider: str) -> CircuitBreaker:
        if provider not in self._breakers:
            config = self._config if self._config else CircuitBreakerConfig()
            self._breakers[provider] = CircuitBreaker(provider=provider, config=config)
        return self._breakers[provider]

    def is_available(self, provider: str) -> bool:
        breaker = self.get_breaker(provider)
        return breaker.state != CircuitState.OPEN

    async def call(
        self,
        provider: str,
        fn: Callable[[], Awaitable[Any]],
        request_start: Optional[float] = None,
    ) -> Any:
        breaker = self.get_breaker(provider)
        if breaker.state == CircuitState.OPEN:
            raise CircuitOpenError(provider, "Circuit is open")
        start_time = request_start or time.time()
        try:
            result = await fn()
            latency_ms = (time.time() - start_time) * 1000
            breaker.latency_samples.append(latency_ms)
            if len(breaker.latency_samples) > 60:
                breaker.latency_samples = breaker.latency_samples[-60:]
            breaker._record_success()
            return result
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            breaker.latency_samples.append(latency_ms)
            if len(breaker.latency_samples) > 60:
                breaker.latency_samples = breaker.latency_samples[-60:]
            reason = str(e)
            breaker._record_failure(reason)
            raise

    def get_status(self, provider: str) -> CircuitStatus:
        return self.get_breaker(provider).get_status()

    def get_all_status(self) -> Dict[str, CircuitStatus]:
        return {provider: breaker.get_status() for provider, breaker in self._breakers.items()}

    def force_open(self, provider: str) -> None:
        self.get_breaker(provider).force_open()

    def reset(self, provider: str) -> None:
        self.get_breaker(provider).reset()

    def reset_all(self) -> None:
        for breaker in self._breakers.values():
            breaker.reset()


class CircuitOpenError(Exception):
    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"Circuit open for {provider}: {message}")