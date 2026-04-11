"""
Tip registry for managing tip definitions.

This module provides the TipRegistry class for registering, retrieving,
and filtering tips based on relevance and context.
"""

import random
from typing import Dict, List, Optional

from api_server.services.tips.types import Tip, TipContext
from api_server.services.tips.history import get_sessions_since_last_shown


class TipRegistry:
    """
    Manages tip definitions and provides tip retrieval functionality.
    
    This class acts as a central registry for all tips, supporting
    registration, retrieval by ID, listing all tips, and getting
    random or contextually relevant tips.
    """
    
    def __init__(self):
        self._tips: Dict[str, Tip] = {}
        self._external_tips: List[Tip] = []
        self._internal_tips: List[Tip] = []
    
    def register_tip(self, tip: Tip) -> None:
        """
        Register a new tip in the registry.
        
        Args:
            tip: The Tip instance to register
        """
        self._tips[tip.id] = tip
    
    def register_external_tip(self, tip: Tip) -> None:
        """
        Register a tip as an external (user-facing) tip.
        
        Args:
            tip: The Tip instance to register
        """
        self._external_tips.append(tip)
        self._tips[tip.id] = tip
    
    def register_internal_tip(self, tip: Tip) -> None:
        """
        Register a tip as an internal tip.
        
        Args:
            tip: The Tip instance to register
        """
        self._internal_tips.append(tip)
        self._tips[tip.id] = tip
    
    def get_tip(self, tip_id: str) -> Optional[Tip]:
        """
        Get a tip by its unique identifier.
        
        Args:
            tip_id: The unique identifier of the tip
            
        Returns:
            The Tip instance if found, None otherwise
        """
        return self._tips.get(tip_id)
    
    def list_tips(self) -> List[Tip]:
        """
        List all registered tips.
        
        Returns:
            List of all registered Tip instances
        """
        return list(self._tips.values())
    
    def list_external_tips(self) -> List[Tip]:
        """
        List all external tips.
        
        Returns:
            List of external Tip instances
        """
        return list(self._external_tips)
    
    def list_internal_tips(self) -> List[Tip]:
        """
        List all internal tips.
        
        Returns:
            List of internal Tip instances
        """
        return list(self._internal_tips)
    
    def get_random_tip(self) -> Optional[Tip]:
        """
        Get a random tip from the registry.
        
        Returns:
            A random Tip instance, or None if no tips exist
        """
        if not self._tips:
            return None
        return random.choice(list(self._tips.values()))
    
    async def get_relevant_tips(
        self,
        context: Optional[TipContext] = None,
    ) -> List[Tip]:
        """
        Get tips that are relevant to the current context.
        
        Filters tips based on:
        1. Whether the tip's is_relevant function returns True
        2. Whether enough sessions have passed since last showing
        
        Args:
            context: Optional context for relevance checking
            
        Returns:
            List of tips that should be shown
        """
        all_tips = [*self._external_tips, *self._internal_tips]
        
        relevant_tips: List[Tip] = []
        for tip in all_tips:
            try:
                is_relevant = await tip.is_relevant(context)
                if not is_relevant:
                    continue
            except Exception:
                continue
            
            sessions_since = get_sessions_since_last_shown(tip.id)
            if sessions_since >= tip.cooldown_sessions:
                relevant_tips.append(tip)
        
        return relevant_tips
    
    def get_tips_by_cooldown(self, cooldown_sessions: int) -> List[Tip]:
        """
        Get all tips with a specific cooldown period.
        
        Args:
            cooldown_sessions: Number of sessions between showings
            
        Returns:
            List of tips with the specified cooldown
        """
        return [
            tip for tip in self._tips.values()
            if tip.cooldown_sessions == cooldown_sessions
        ]
    
    def remove_tip(self, tip_id: str) -> bool:
        """
        Remove a tip from the registry.
        
        Args:
            tip_id: The unique identifier of the tip to remove
            
        Returns:
            True if the tip was removed, False if not found
        """
        if tip_id not in self._tips:
            return False
        
        tip = self._tips[tip_id]
        del self._tips[tip_id]
        
        if tip in self._external_tips:
            self._external_tips.remove(tip)
        if tip in self._internal_tips:
            self._internal_tips.remove(tip)
        
        return True
    
    def clear(self) -> None:
        """Remove all tips from the registry."""
        self._tips.clear()
        self._external_tips.clear()
        self._internal_tips.clear()


_default_registry: Optional[TipRegistry] = None


def get_default_registry() -> TipRegistry:
    """Get the default global TipRegistry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = TipRegistry()
    return _default_registry


def register_tip(tip: Tip) -> None:
    """Register a tip in the default registry."""
    get_default_registry().register_tip(tip)


def get_tip(tip_id: str) -> Optional[Tip]:
    """Get a tip by ID from the default registry."""
    return get_default_registry().get_tip(tip_id)


def list_tips() -> List[Tip]:
    """List all tips from the default registry."""
    return get_default_registry().list_tips()


def get_random_tip() -> Optional[Tip]:
    """Get a random tip from the default registry."""
    return get_default_registry().get_random_tip()


async def get_relevant_tips(
    context: Optional[TipContext] = None,
) -> List[Tip]:
    """Get relevant tips from the default registry."""
    return await get_default_registry().get_relevant_tips(context)
