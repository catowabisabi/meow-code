"""
FastAPI routes for provider health and circuit breaker status.
"""
import time
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.circuit_breaker import CircuitBreakerService, CircuitState

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderStatus(BaseModel):
    state: str
    failure_count: int
    last_failure_time: Optional[float] = None
    last_failure_reason: Optional[str] = None


class ProviderHealthResponse(BaseModel):
    providers: Dict[str, ProviderStatus]


class HeartbeatEntry(BaseModel):
    provider_id: str
    latency_samples: List[int]  # last 60 samples in ms
    circuit_state_history: List[Dict[str, Any]]  # [{timestamp, from_state, to_state}]
    failure_timestamps: List[float]
    custom_thresholds: Dict[str, Any]  # {latency_ms: int, failure_count: int}


class ProviderHeartbeatResponse(BaseModel):
    providers: List[HeartbeatEntry]
    server_time: float


@router.get("/health", response_model=ProviderHealthResponse)
async def get_providers_health() -> ProviderHealthResponse:
    cb_service = CircuitBreakerService.get_instance()
    all_status = cb_service.get_all_status()
    provider_statuses = {}
    for provider, status in all_status.items():
        provider_statuses[provider] = ProviderStatus(
            state=status.state.value,
            failure_count=status.failure_count,
            last_failure_time=status.last_failure_time,
            last_failure_reason=status.last_failure_reason,
        )
    return ProviderHealthResponse(providers=provider_statuses)


@router.post("/{provider}/reset")
async def reset_provider_circuit(provider: str) -> Dict[str, Any]:
    cb_service = CircuitBreakerService.get_instance()
    cb_service.reset(provider)
    return {"ok": True, "provider": provider, "state": "closed"}


@router.post("/{provider}/force-open")
async def force_provider_open(provider: str) -> Dict[str, Any]:
    cb_service = CircuitBreakerService.get_instance()
    cb_service.force_open(provider)
    return {"ok": True, "provider": provider, "state": "open"}


@router.get("/order")
async def get_provider_order() -> Dict[str, Any]:
    from ..services.provider_chain import ProviderChain
    chain = ProviderChain.get_instance()
    return {"order": chain.get_provider_order()}


@router.put("/order")
async def set_provider_order(order: list) -> Dict[str, Any]:
    from ..services.provider_chain import ProviderChain
    chain = ProviderChain.get_instance()
    chain.set_provider_order(order)
    return {"ok": True, "order": order}


# Default thresholds — can be overridden per-provider in config
DEFAULT_LATENCY_MS = 2000
DEFAULT_FAILURE_COUNT = 5


@router.get("/heartbeat", response_model=ProviderHeartbeatResponse)
async def get_provider_heartbeat() -> ProviderHeartbeatResponse:
    """
    Return rolling time-series health data per provider.

    latency_samples: last 60 request latencies in ms (empty until 60 samples collected)
    circuit_state_history: all state transitions from last 24h
    failure_timestamps: all failure timestamps from last 24h
    """
    cb_service = CircuitBreakerService.get_instance()
    server_time = time.time()
    # 24h cutoff
    cutoff = server_time - 86400

    entries: List[HeartbeatEntry] = []
    for provider, breaker in cb_service._breakers.items():
        # Filter history to last 24h
        filtered_history = [
            h for h in breaker.circuit_state_history
            if h.get("timestamp", 0) > cutoff
        ]
        # Filter failure timestamps to last 24h
        filtered_failures = [t for t in breaker.failure_timestamps if t > cutoff]
        # Convert latency floats to ints
        latency_ints = [int(x) for x in breaker.latency_samples[-60:]]

        entries.append(HeartbeatEntry(
            provider_id=provider,
            latency_samples=latency_ints,
            circuit_state_history=filtered_history,
            failure_timestamps=filtered_failures,
            custom_thresholds={
                "latency_ms": DEFAULT_LATENCY_MS,
                "failure_count": DEFAULT_FAILURE_COUNT,
            },
        ))

    return ProviderHeartbeatResponse(providers=entries, server_time=server_time)