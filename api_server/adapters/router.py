"""
Adapter router for unified AI provider access.
"""
import logging
from typing import Dict, AsyncIterator, List, Optional

from ..models.message import Message
from ..models.tool import ToolDefinition
from .base import BaseAdapter, ChatEvent

logger = logging.getLogger(__name__)

RETRYABLE_CODES = {429, 502, 503, 504}


class AdapterRouter:
    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._default_provider: Optional[str] = None

    def register_adapter(self, name: str, adapter: BaseAdapter, set_default: bool = False) -> None:
        self._adapters[name] = adapter
        if set_default or self._default_provider is None:
            self._default_provider = name

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        return self._adapters.get(name)

    def get_default_provider(self) -> Optional[str]:
        return self._default_provider

    async def route_chat(
        self,
        provider: str,
        messages: List[Message],
        model: str,
        system_prompt: str = "",
        tools: List[ToolDefinition] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[ChatEvent]:
        from ..services.circuit_breaker import CircuitBreakerService, CircuitOpenError
        cb_service = CircuitBreakerService.get_instance()
        adapter = self._adapters.get(provider)

        if not adapter:
            error_msg = f"No adapter registered for provider: {provider}"
            yield ChatEvent.stream_error(error=error_msg, index=0)
            return

        if tools is None:
            tools = []

        try:
            async for event in cb_service.call(
                provider,
                lambda: adapter.chat(
                    messages=messages,
                    model=model,
                    system_prompt=system_prompt,
                    tools=tools,
                    stream=stream,
                    **kwargs
                )
            ):
                if event.type == "stream_error" and event.error:
                    for code in RETRYABLE_CODES:
                        if str(code) in event.error:
                            logger.warning(f"Retryable error from {provider}: {event.error}")
                            break
                yield event
        except CircuitOpenError:
            yield ChatEvent.stream_error(error=f"Circuit open for {provider}", index=0)
        except Exception as e:
            logger.error(f"Provider {provider} error: {e}")
            yield ChatEvent.stream_error(error=str(e), index=0)

    async def test_connection(self, provider: str) -> bool:
        adapter = self._adapters.get(provider)
        if not adapter:
            return False
        return await adapter.test_connection()

    @property
    def registered_providers(self) -> List[str]:
        return list(self._adapters.keys())