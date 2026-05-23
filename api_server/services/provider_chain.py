"""
ProviderChain - Multi-provider fallback with circuit breaker integration.

Manages ordered list of providers and attempts them in sequence,
skipping providers with open circuits.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator

from ..adapters.base import ChatEvent
from ..services.circuit_breaker import CircuitBreakerService, CircuitOpenError

logger = logging.getLogger(__name__)

PROVIDER_CHAIN_CONFIG_PATH = Path.home() / ".claude" / "provider_chain.json"

DEFAULT_PROVIDER_ORDER = ["anthropic", "openai", "deepseek", "minimax", "ollama"]

RETRYABLE_CODES = {429, 502, 503, 504}


def _is_retryable_error(event: ChatEvent) -> bool:
    if event.type != "stream_error":
        return False
    error_str = event.error or ""
    for code in RETRYABLE_CODES:
        if str(code) in error_str:
            return True
    return False


def _load_provider_chain() -> List[str]:
    if PROVIDER_CHAIN_CONFIG_PATH.exists():
        try:
            with open(PROVIDER_CHAIN_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("order", DEFAULT_PROVIDER_ORDER)
        except Exception:
            pass
    return DEFAULT_PROVIDER_ORDER


def _save_provider_chain(order: List[str]) -> None:
    PROVIDER_CHAIN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVIDER_CHAIN_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"order": order}, f, ensure_ascii=False, indent=2)


class ProviderChain:
    _instance: Optional["ProviderChain"] = None

    def __init__(self):
        self._circuit_breaker = CircuitBreakerService.get_instance()
        self._provider_order: List[str] = _load_provider_chain()
        self._active_provider: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ProviderChain":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_provider_order(self) -> List[str]:
        return list(self._provider_order)

    def set_provider_order(self, order: List[str]) -> None:
        self._provider_order = order
        _save_provider_chain(order)

    def get_active_provider(self) -> Optional[str]:
        return self._active_provider

    async def invoke(
        self,
        router,
        messages: List[Any],
        model: str,
        system_prompt: str = "",
        tools: Optional[List[Any]] = None,
        provider_preference: Optional[str] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[ChatEvent]:
        providers_to_try = self._get_providers_list(provider_preference)
        last_error: Optional[Exception] = None

        for provider in providers_to_try:
            if not self._circuit_breaker.is_available(provider):
                logger.info(f"Skipping provider {provider} - circuit open")
                continue

            self._active_provider = provider
            try:
                async for event in self._circuit_breaker.call(
                    provider,
                    lambda: router.route_chat(
                        provider=provider,
                        messages=messages,
                        model=model,
                        system_prompt=system_prompt,
                        tools=tools,
                        stream=stream,
                        **kwargs
                    )
                ):
                    if _is_retryable_error(event):
                        logger.warning(f"Retryable error from {provider}: {event.error}")
                        break
                    yield event

                if event.type == "stream_end":
                    return

            except CircuitOpenError:
                logger.info(f"Circuit open for {provider}, trying next provider")
                continue
            except Exception as e:
                last_error = e
                logger.error(f"Provider {provider} failed: {e}")
                continue

        if last_error:
            yield ChatEvent.stream_error(error=str(last_error), index=0)
        else:
            yield ChatEvent.stream_error(error="All providers exhausted", index=0)

    def _get_providers_list(self, preference: Optional[str]) -> List[str]:
        if preference and preference in self._provider_order:
            pref_idx = self._provider_order.index(preference)
            result = [preference] + [
                p for p in self._provider_order if p != preference
            ]
            return result
        return list(self._provider_order)


async def invoke_with_fallback(
    router,
    messages: List[Any],
    model: str,
    system_prompt: str = "",
    tools: Optional[List[Any]] = None,
    provider_preference: Optional[str] = None,
    stream: bool = True,
    **kwargs
) -> AsyncIterator[ChatEvent]:
    chain = ProviderChain.get_instance()
    async for event in chain.invoke(
        router=router,
        messages=messages,
        model=model,
        system_prompt=system_prompt,
        tools=tools,
        provider_preference=provider_preference,
        stream=stream,
        **kwargs
    ):
        yield event