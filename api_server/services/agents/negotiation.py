import asyncio
import uuid
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

class NegotiationState(Enum):
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class NegotiationType(Enum):
    TASK_DELEGATION = "task_delegation"
    RESOURCE_ALLOCATION = "resource_allocation"
    WORKFLOW_COORDINATION = "workflow_coordination"
    CONFLICT_RESOLUTION = "conflict_resolution"

@dataclass
class NegotiationOffer:
    id: str
    negotiation_type: NegotiationType
    proposer: str
    recipient: str
    terms: Dict[str, Any]
    state: NegotiationState = NegotiationState.PROPOSED
    counter_offers: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NegotiationResult:
    success: bool
    offer_id: str
    state: NegotiationState
    final_terms: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class NegotiationProtocol:
    def __init__(self, message_broker=None):
        self._broker = message_broker
        self._negotiations: Dict[str, NegotiationOffer] = {}
        self._handlers: Dict[str, Callable] = {}
        self._default_timeout: float = 300.0
        self._locks: Dict[str, asyncio.Lock] = {}

    async def propose(
        self,
        negotiation_type: NegotiationType,
        proposer: str,
        recipient: str,
        terms: Dict[str, Any],
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        offer_id = str(uuid.uuid4())

        offer = NegotiationOffer(
            id=offer_id,
            negotiation_type=negotiation_type,
            proposer=proposer,
            recipient=recipient,
            terms=terms,
            expires_at=time.time() + (timeout or self._default_timeout),
            metadata=metadata or {},
        )

        self._negotiations[offer_id] = offer

        if proposer not in self._locks:
            self._locks[proposer] = asyncio.Lock()
        if recipient not in self._locks:
            self._locks[recipient] = asyncio.Lock()

        return offer_id

    async def accept(
        self,
        offer_id: str,
        acceptor: str,
    ) -> NegotiationResult:
        offer = self._negotiations.get(offer_id)
        if not offer:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=NegotiationState.EXPIRED,
                message="Offer not found",
            )

        if offer.state != NegotiationState.PROPOSED and offer.state != NegotiationState.NEGOTIATING:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=offer.state,
                message=f"Cannot accept offer in state {offer.state.value}",
            )

        if time.time() > (offer.expires_at or 0):
            offer.state = NegotiationState.EXPIRED
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=NegotiationState.EXPIRED,
                message="Offer has expired",
            )

        offer.state = NegotiationState.ACCEPTED

        return NegotiationResult(
            success=True,
            offer_id=offer_id,
            state=NegotiationState.ACCEPTED,
            final_terms=offer.terms,
        )

    async def reject(
        self,
        offer_id: str,
        rejector: str,
        reason: Optional[str] = None,
    ) -> NegotiationResult:
        offer = self._negotiations.get(offer_id)
        if not offer:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=NegotiationState.EXPIRED,
                message="Offer not found",
            )

        offer.state = NegotiationState.REJECTED
        if reason:
            offer.metadata["rejection_reason"] = reason

        return NegotiationResult(
            success=False,
            offer_id=offer_id,
            state=NegotiationState.REJECTED,
            message=reason or "Offer rejected",
        )

    async def counter_propose(
        self,
        offer_id: str,
        counter_proposer: str,
        new_terms: Dict[str, Any],
    ) -> NegotiationResult:
        offer = self._negotiations.get(offer_id)
        if not offer:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=NegotiationState.EXPIRED,
                message="Offer not found",
            )

        if offer.state != NegotiationState.PROPOSED and offer.state != NegotiationState.NEGOTIATING:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=offer.state,
                message=f"Cannot counter-propose in state {offer.state.value}",
            )

        offer.counter_offers.append({
            "terms": new_terms,
            "proposer": counter_proposer,
            "timestamp": time.time(),
        })

        offer.state = NegotiationState.NEGOTIATING
        offer.terms = new_terms
        offer.expires_at = time.time() + self._default_timeout

        return NegotiationResult(
            success=True,
            offer_id=offer_id,
            state=NegotiationState.NEGOTIATING,
            final_terms=new_terms,
        )

    async def withdraw(
        self,
        offer_id: str,
        withdrawer: str,
    ) -> NegotiationResult:
        offer = self._negotiations.get(offer_id)
        if not offer:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=NegotiationState.EXPIRED,
                message="Offer not found",
            )

        if offer.proposer != withdrawer:
            return NegotiationResult(
                success=False,
                offer_id=offer_id,
                state=offer.state,
                message="Only proposer can withdraw",
            )

        offer.state = NegotiationState.WITHDRAWN

        return NegotiationResult(
            success=True,
            offer_id=offer_id,
            state=NegotiationState.WITHDRAWN,
        )

    async def get_offer(
        self,
        offer_id: str,
    ) -> Optional[NegotiationOffer]:
        return self._negotiations.get(offer_id)

    async def get_pending_offers(
        self,
        agent_id: str,
        include_proposer: bool = True,
        include_recipient: bool = True,
    ) -> List[NegotiationOffer]:
        offers = []

        for offer in self._negotiations.values():
            if offer.state not in (NegotiationState.PROPOSED, NegotiationState.NEGOTIATING):
                continue

            if time.time() > (offer.expires_at or 0):
                offer.state = NegotiationState.EXPIRED
                continue

            if include_proposer and offer.proposer == agent_id:
                offers.append(offer)
            elif include_recipient and offer.recipient == agent_id:
                offers.append(offer)

        return offers

    async def expire_offers(self):
        current_time = time.time()

        for offer in self._negotiations.values():
            if offer.state in (NegotiationState.PROPOSED, NegotiationState.NEGOTIATING):
                if current_time > (offer.expires_at or 0):
                    offer.state = NegotiationState.EXPIRED

_negotiation_protocol: Optional[NegotiationProtocol] = None

def get_negotiation_protocol() -> NegotiationProtocol:
    global _negotiation_protocol
    if _negotiation_protocol is None:
        _negotiation_protocol = NegotiationProtocol()
    return _negotiation_protocol
