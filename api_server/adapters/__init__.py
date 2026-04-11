"""
AI Provider Adapters.

Unified adapter system for multi-provider AI access.
"""
from .base import BaseAdapter, ChatEvent
from .anthropic import AnthropicAdapter
from .openai import OpenAIAdapter
from .deepseek import DeepSeekAdapter
from .minimax import MiniMaxAdapter
from .ollama import OllamaAdapter
from .router import AdapterRouter

__all__ = [
    "BaseAdapter",
    "ChatEvent",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "DeepSeekAdapter",
    "MiniMaxAdapter",
    "OllamaAdapter",
    "AdapterRouter",
]
