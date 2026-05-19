import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

class DeliveryStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class DeliveryConfirmation:
    message_id: str
    status: DeliveryStatus
    delivered_at: Optional[float] = None
    attempts: int = 0
    last_error: Optional[str] = None

class DeliveryManager:
    def __init__(self, message_broker=None):
        self._broker = message_broker
        self._confirmations: Dict[str, DeliveryConfirmation] = {}
        self._retry_delays: Dict[str, float] = {
            1: 1.0,
            2: 5.0,
            3: 15.0,
            4: 30.0,
            5: 60.0,
        }
        self._max_retries = 5
        self._handlers: Dict[str, Callable] = {}

    async def confirm_delivery(
        self,
        message_id: str,
        success: bool,
        error: Optional[str] = None,
    ):
        if message_id not in self._confirmations:
            self._confirmations[message_id] = DeliveryConfirmation(
                message_id=message_id,
                status=DeliveryStatus.PENDING,
            )
        
        confirmation = self._confirmations[message_id]
        confirmation.attempts += 1
        
        if success:
            confirmation.status = DeliveryStatus.DELIVERED
            confirmation.delivered_at = time.time()
        else:
            confirmation.last_error = error
            
            if confirmation.attempts >= self._max_retries:
                confirmation.status = DeliveryStatus.FAILED
            else:
                confirmation.status = DeliveryStatus.RETRYING
                delay = self._retry_delays.get(confirmation.attempts, 60.0)
                asyncio.create_task(self._schedule_retry(message_id, delay))

    async def _schedule_retry(self, message_id: str, delay: float):
        await asyncio.sleep(delay)
        confirmation = self._confirmations.get(message_id)
        if confirmation and confirmation.status == DeliveryStatus.RETRYING:
            handler = self._handlers.get(message_id)
            if handler:
                try:
                    await handler(message_id)
                except Exception as e:
                    await self.confirm_delivery(message_id, False, str(e))

    async def get_confirmation(
        self,
        message_id: str,
    ) -> Optional[DeliveryConfirmation]:
        return self._confirmations.get(message_id)

    async def register_handler(
        self,
        message_id: str,
        handler: Callable,
    ):
        self._handlers[message_id] = handler

    async def get_pending_deliveries(
        self,
        agent_id: str,
    ) -> List[DeliveryConfirmation]:
        if not self._broker:
            return []
        
        messages = await self._broker.get_messages(
            agent_id=agent_id,
            only_unread=True,
        )
        
        pending = []
        for msg in messages:
            conf = self._confirmations.get(msg.id)
            if conf and conf.status in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING):
                pending.append(conf)
            elif not conf:
                pending.append(DeliveryConfirmation(
                    message_id=msg.id,
                    status=DeliveryStatus.PENDING,
                ))
        
        return pending

    async def retry_failed(
        self,
        agent_id: str,
    ) -> int:
        if not self._broker:
            return 0
        
        count = await self._broker.requeue_pending(agent_id)
        return count

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._confirmations)
        delivered = sum(
            1 for c in self._confirmations.values()
            if c.status == DeliveryStatus.DELIVERED
        )
        failed = sum(
            1 for c in self._confirmations.values()
            if c.status == DeliveryStatus.FAILED
        )
        pending = sum(
            1 for c in self._confirmations.values()
            if c.status in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING)
        )
        
        return {
            "total": total,
            "delivered": delivered,
            "failed": failed,
            "pending": pending,
            "delivery_rate": delivered / total if total > 0 else 0.0,
        }

_delivery_manager: Optional[DeliveryManager] = None

def get_delivery_manager() -> DeliveryManager:
    global _delivery_manager
    if _delivery_manager is None:
        _delivery_manager = DeliveryManager()
    return _delivery_manager