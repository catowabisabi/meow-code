"""
FastAPI routes for provider health and circuit breaker status.
"""
from typing import Dict, Any, Optional

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