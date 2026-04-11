"""
API-based microcompact implementation using native context management.

This module provides the API-side microcompact functionality that uses native
context management strategies instead of CLI-side compaction. Ported from
the TypeScript apiMicrocompact.ts.

Docs: https://docs.google.com/document/d/1oCT4evvWTh3P6z-kcfNQwWTCxAhkoFndSaNS9Gm40uw/edit?tab=t.0
"""

import os
from dataclasses import dataclass, field
from typing import Any, Optional, Union

# Default values for context management strategies
# Match client-side microcompact token values
DEFAULT_MAX_INPUT_TOKENS = 180_000
DEFAULT_TARGET_INPUT_TOKENS = 40_000

# Tool names that can have their results cleared
TOOLS_CLEARABLE_RESULTS = [
    "BashTool",
    "GlobTool",
    "GrepTool",
    "FileReadTool",
    "WebFetchTool",
    "WebSearchTool",
]

# Tool names that can have their uses cleared
TOOLS_CLEARABLE_USES = [
    "FileEditTool",
    "FileWriteTool",
    "NotebookEditTool",
]


@dataclass
class ContextEditTrigger:
    """Trigger condition for context editing strategy."""
    type: str = "input_tokens"
    value: int = DEFAULT_MAX_INPUT_TOKENS


@dataclass
class ContextEditKeep:
    """What to keep in the context edit strategy."""
    type: str = "tool_uses"
    value: int = 10


@dataclass
class ContextEditClearAtLeast:
    """Minimum amount to clear in context edit strategy."""
    type: str = "input_tokens"
    value: int = 140_000


@dataclass
class ClearToolUsesStrategy:
    """
    Context edit strategy that clears tool uses.
    
    Ported from TypeScript: { type: 'clear_tool_uses_20250919', ... }
    """
    type: str = "clear_tool_uses_20250919"
    trigger: Optional[ContextEditTrigger] = None
    keep: Optional[ContextEditKeep] = None
    clear_tool_inputs: Union[bool, list[str]] = True
    exclude_tools: list[str] = field(default_factory=list)
    clear_at_least: Optional[ContextEditClearAtLeast] = None


@dataclass
class ClearThinkingStrategy:
    """
    Context edit strategy that clears thinking blocks.
    
    Ported from TypeScript: { type: 'clear_thinking_20251015', ... }
    """
    type: str = "clear_thinking_20251015"
    keep: Union[ContextEditKeep, str] = field(default_factory="all")


ContextEditStrategy = Union[ClearToolUsesStrategy, ClearThinkingStrategy]


@dataclass
class ContextManagementConfig:
    """Context management configuration wrapper."""
    edits: list[ContextEditStrategy] = field(default_factory=list)


def _is_env_truthy(env_value: Optional[str]) -> bool:
    """Check if an environment variable is set to a truthy value."""
    if env_value is None:
        return False
    return env_value.lower() in ("true", "1", "yes", "on")


def _get_env_int(env_name: str, default: int) -> int:
    """Get an integer from environment variable with default."""
    value = os.environ.get(env_name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_use_api_clear_tool_results() -> bool:
    """Check if API clear tool results is enabled."""
    return _is_env_truthy(os.environ.get("USE_API_CLEAR_TOOL_RESULTS"))


def _get_use_api_clear_tool_uses() -> bool:
    """Check if API clear tool uses is enabled."""
    return _is_env_truthy(os.environ.get("USE_API_CLEAR_TOOL_USES"))


def _get_user_type() -> str:
    """Get the user type from environment."""
    return os.environ.get("USER_TYPE", "")


def get_api_context_management(
    has_thinking: bool = False,
    is_redact_thinking_active: bool = False,
    clear_all_thinking: bool = False,
) -> Optional[ContextManagementConfig]:
    """
    Get API-based microcompact configuration using native context management.
    
    This function returns context management strategies that the API uses
    to automatically manage context window size.
    
    Args:
        has_thinking: Whether thinking blocks are present in the conversation
        is_redact_thinking_active: Whether thinking redaction is active
        clear_all_thinking: Whether to clear all thinking (e.g., after long idle)
    
    Returns:
        ContextManagementConfig with edit strategies, or None if no strategies apply
    """
    strategies: list[ContextEditStrategy] = []
    
    # Preserve thinking blocks in previous assistant turns. Skip when
    # redact-thinking is active — redacted blocks have no model-visible content.
    # When clearAllThinking is set (>1h idle = cache miss), keep only the last
    # thinking turn — the API schema requires value >= 1, and omitting the edit
    # falls back to the model-policy default (often "all"), which wouldn't clear.
    if has_thinking and not is_redact_thinking_active:
        if clear_all_thinking:
            keep = ClearThinkingStrategy(
                type="clear_thinking_20251015",
                keep=ContextEditKeep(type="thinking_turns", value=1),
            )
        else:
            keep = ClearThinkingStrategy(
                type="clear_thinking_20251015",
                keep="all",
            )
        strategies.append(keep)
    
    # Tool clearing strategies are ant-only
    if _get_user_type() != "ant":
        return ContextManagementConfig(edits=strategies) if strategies else None
    
    use_clear_tool_results = _get_use_api_clear_tool_results()
    use_clear_tool_uses = _get_use_api_clear_tool_uses()
    
    # If no tool clearing strategy is enabled, return early
    if not use_clear_tool_results and not use_clear_tool_uses:
        return ContextManagementConfig(edits=strategies) if strategies else None
    
    trigger_threshold = _get_env_int("API_MAX_INPUT_TOKENS", DEFAULT_MAX_INPUT_TOKENS)
    keep_target = _get_env_int("API_TARGET_INPUT_TOKENS", DEFAULT_TARGET_INPUT_TOKENS)
    
    if use_clear_tool_results:
        strategy = ClearToolUsesStrategy(
            type="clear_tool_uses_20250919",
            trigger=ContextEditTrigger(
                type="input_tokens",
                value=trigger_threshold,
            ),
            clear_at_least=ContextEditClearAtLeast(
                type="input_tokens",
                value=trigger_threshold - keep_target,
            ),
            clear_tool_inputs=TOOLS_CLEARABLE_RESULTS,
        )
        strategies.append(strategy)
    
    if use_clear_tool_uses:
        strategy = ClearToolUsesStrategy(
            type="clear_tool_uses_20250919",
            trigger=ContextEditTrigger(
                type="input_tokens",
                value=trigger_threshold,
            ),
            clear_at_least=ContextEditClearAtLeast(
                type="input_tokens",
                value=trigger_threshold - keep_target,
            ),
            exclude_tools=TOOLS_CLEARABLE_USES,
        )
        strategies.append(strategy)
    
    return ContextManagementConfig(edits=strategies) if strategies else None


def create_api_microcompact_result(
    messages: list[Any],
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Create API microcompact result with context management strategies.
    
    This is the main entry point for API-side microcompact operations.
    
    Args:
        messages: List of conversation messages
        options: Optional configuration:
            - has_thinking: Whether thinking blocks are present
            - is_redact_thinking_active: Whether thinking redaction is active
            - clear_all_thinking: Whether to clear all thinking
    
    Returns:
        Dict with messages and optional context_management config
    """
    options = options or {}
    
    has_thinking = options.get("has_thinking", False)
    is_redact_thinking_active = options.get("is_redact_thinking_active", False)
    clear_all_thinking = options.get("clear_all_thinking", False)
    
    context_config = get_api_context_management(
        has_thinking=has_thinking,
        is_redact_thinking_active=is_redact_thinking_active,
        clear_all_thinking=clear_all_thinking,
    )
    
    result: dict[str, Any] = {"messages": messages}
    
    if context_config and context_config.edits:
        result["context_management"] = {
            "edits": [_strategy_to_dict(s) for s in context_config.edits]
        }
    
    return result


def _strategy_to_dict(strategy: ContextEditStrategy) -> dict[str, Any]:
    """Convert a ContextEditStrategy to a dictionary."""
    if isinstance(strategy, ClearThinkingStrategy):
        return {
            "type": strategy.type,
            "keep": strategy.keep,
        }
    elif isinstance(strategy, ClearToolUsesStrategy):
        result: dict[str, Any] = {"type": strategy.type}
        if strategy.trigger:
            result["trigger"] = {
                "type": strategy.trigger.type,
                "value": strategy.trigger.value,
            }
        if strategy.keep:
            result["keep"] = {
                "type": strategy.keep.type,
                "value": strategy.keep.value,
            }
        if strategy.clear_tool_inputs is not None:
            result["clear_tool_inputs"] = strategy.clear_tool_inputs
        if strategy.exclude_tools:
            result["exclude_tools"] = strategy.exclude_tools
        if strategy.clear_at_least:
            result["clear_at_least"] = {
                "type": strategy.clear_at_least.type,
                "value": strategy.clear_at_least.value,
            }
        return result
    else:
        # Fallback for unknown strategy types
        return {"type": str(strategy)}


class ApiMicroCompactor:
    """
    API-side microcompactor for context management.
    
    This class provides a convenient interface for API-based microcompact
    operations using native context management strategies.
    """
    
    def __init__(self):
        self._max_input_tokens = DEFAULT_MAX_INPUT_TOKENS
        self._target_input_tokens = DEFAULT_TARGET_INPUT_TOKENS
    
    @property
    def max_input_tokens(self) -> int:
        """Get the maximum input tokens threshold."""
        return self._max_input_tokens
    
    @max_input_tokens.setter
    def max_input_tokens(self, value: int) -> None:
        """Set the maximum input tokens threshold."""
        self._max_input_tokens = value
    
    @property
    def target_input_tokens(self) -> int:
        """Get the target input tokens."""
        return self._target_input_tokens
    
    @target_input_tokens.setter
    def target_input_tokens(self, value: int) -> None:
        """Set the target input tokens."""
        self._target_input_tokens = value
    
    def compact(
        self,
        messages: list[Any],
        options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Apply microcompact to messages using API context management.
        
        Args:
            messages: List of conversation messages
            options: Optional configuration options
        
        Returns:
            Dict with compacted messages and context_management config
        """
        return create_api_microcompact_result(messages, options)
    
    def get_strategy(
        self,
        has_thinking: bool = False,
        is_redact_thinking_active: bool = False,
    ) -> Optional[ContextManagementConfig]:
        """
        Get the context management strategy without applying it.
        
        Args:
            has_thinking: Whether thinking blocks are present
            is_redact_thinking_active: Whether thinking redaction is active
        
        Returns:
            ContextManagementConfig if strategies are applicable, None otherwise
        """
        return get_api_context_management(
            has_thinking=has_thinking,
            is_redact_thinking_active=is_redact_thinking_active,
        )


__all__ = [
    "ApiMicroCompactor",
    "ClearThinkingStrategy",
    "ClearToolUsesStrategy",
    "ContextEditClearAtLeast",
    "ContextEditKeep",
    "ContextEditStrategy",
    "ContextEditTrigger",
    "ContextManagementConfig",
    "DEFAULT_MAX_INPUT_TOKENS",
    "DEFAULT_TARGET_INPUT_TOKENS",
    "TOOLS_CLEARABLE_RESULTS",
    "TOOLS_CLEARABLE_USES",
    "create_api_microcompact_result",
    "get_api_context_management",
]
