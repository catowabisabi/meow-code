"""
Forked agent execution for auto-dream consolidation.

This module adapts the TypeScript runForkedAgent concept to Python by:
- Using query_haiku() for lighter tasks
- Using query_model_without_streaming() for larger model tasks
- Running with cache-safe params in an isolated context
- Yielding messages via on_message callback
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional

from ..api.claude import (
    HAIKU_MODEL,
    QueryHaikuOptions,
    QueryModelOptions,
    query_haiku,
    query_model_without_streaming,
)
from .types import CacheSafeParams, ForkAgentResult


TOOL_USE_BLOCK_NAMES = {"FileRead", "Grep", "Glob", "Bash", "FileEdit", "FileWrite"}


async def run_forked_agent(
    prompt_messages: List[Dict[str, Any]],
    cache_safe_params: CacheSafeParams,
    can_use_tool: Callable[[Any, Dict[str, Any]], Dict[str, Any]],
    query_source: str,
    fork_label: str,
    skip_transcript: bool = True,
    max_turns: Optional[int] = None,
    abort_controller: Optional[asyncio.Event] = None,
    on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> ForkAgentResult:
    """
    Run a forked agent for dream consolidation.
    
    This runs an isolated agent context with the same cache-safe parameters
    but with a fresh prompt context for consolidation.
    
    Args:
        prompt_messages: Initial prompt messages for the agent.
        cache_safe_params: Cache-safe model parameters.
        can_use_tool: Function to check tool permissions.
        query_source: Source identifier for the query.
        fork_label: Label for this forked agent.
        skip_transcript: Whether to skip transcript recording.
        max_turns: Maximum number of turns (default: 50).
        abort_controller: Optional event to check for abort.
        on_message: Optional callback for yielded messages.
    
    Returns:
        ForkAgentResult with success status, messages, and output.
    """
    if max_turns is None:
        max_turns = 50
    
    turns_remaining = max_turns
    all_messages: List[Dict[str, Any]] = []
    tool_use_count = 0
    
    current_messages = list(prompt_messages)
    
    while turns_remaining > 0:
        if abort_controller and abort_controller.is_set():
            return ForkAgentResult(
                success=False,
                messages=all_messages,
                output="",
                error="Aborted by controller",
            )
        
        try:
            if fork_label == "haiku" or HAIKU_MODEL in cache_safe_params.model:
                result = await _run_haiku_turn(
                    messages=current_messages,
                    cache_safe_params=cache_safe_params,
                    abort_controller=abort_controller,
                )
            else:
                result = await _run_model_turn(
                    messages=current_messages,
                    cache_safe_params=cache_safe_params,
                    abort_controller=abort_controller,
                )
            
            if result is None:
                break
            
            all_messages.append(result)
            
            if on_message:
                on_message(result)
            
            if not result.get("content"):
                break
            
            content = result["content"]
            if isinstance(content, list):
                has_tool_use = any(
                    block.get("type") == "tool_use"
                    for block in content
                    if isinstance(block, dict)
                )
                if not has_tool_use:
                    turns_remaining = 0
                    break
                
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_use_count += 1
            elif isinstance(content, str):
                turns_remaining = 0
                break
            
            current_messages.append(result)
            turns_remaining -= 1
            
        except Exception as e:
            return ForkAgentResult(
                success=False,
                messages=all_messages,
                output="",
                error=str(e),
            )
    
    output_text = _extract_text_from_messages(all_messages)
    
    return ForkAgentResult(
        success=True,
        messages=all_messages,
        output=output_text,
    )


async def _run_haiku_turn(
    messages: List[Dict[str, Any]],
    cache_safe_params: CacheSafeParams,
    abort_controller: Optional[asyncio.Event],
) -> Optional[Dict[str, Any]]:
    """Run a single turn using the Haiku model."""
    if abort_controller and abort_controller.is_set():
        return None
    
    last_message = messages[-1] if messages else None
    user_content = ""
    if last_message and last_message.get("role") == "user":
        if isinstance(last_message.get("content"), str):
            user_content = last_message["content"]
        elif isinstance(last_message.get("content"), list):
            for block in last_message["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    user_content = block.get("text", "")
                    break
    
    try:
        client = _get_anthropic_client()
        result = await query_haiku(
            client=client,
            options=QueryHaikuOptions(
                system_prompt=cache_safe_params.system_prompt,
                user_prompt=user_content,
                query_source="auto_dream_haiku",
            ),
        )
        
        return {
            "role": "assistant",
            "content": result.get("message", {}).get("content", []),
        }
    except Exception:
        return None


async def _run_model_turn(
    messages: List[Dict[str, Any]],
    cache_safe_params: CacheSafeParams,
    abort_controller: Optional[asyncio.Event],
) -> Optional[Dict[str, Any]]:
    """Run a single turn using the full model."""
    if abort_controller and abort_controller.is_set():
        return None
    
    try:
        client = _get_anthropic_client()
        options = QueryModelOptions(
            model=cache_safe_params.model,
            messages=messages,
            max_tokens=4096,
            system=cache_safe_params.system_prompt,
            tools=cache_safe_params.tools,
            stream=False,
            thinking=cache_safe_params.thinking_config if cache_safe_params.thinking_config else None,
        )
        
        result = await query_model_without_streaming(client, options)
        
        content_blocks = []
        for block in result.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    content_blocks.append({
                        "type": "text",
                        "text": block.text if hasattr(block, "text") else "",
                    })
                elif block.type == "tool_use":
                    content_blocks.append({
                        "type": "tool_use",
                        "id": block.id if hasattr(block, "id") else "",
                        "name": block.name if hasattr(block, "name") else "",
                        "input": block.input if hasattr(block, "input") else {},
                    })
        
        return {
            "role": "assistant",
            "content": content_blocks,
        }
    except Exception:
        return None


def _get_anthropic_client() -> Any:
    """Get the Anthropic API client."""
    try:
        from ...adapters import get_anthropic_client
        return get_anthropic_client()
    except Exception:
        return _create_basic_client()


def _create_basic_client() -> Any:
    """Create a basic Anthropic client for testing."""
    try:
        import anthropic
        api_key = None
        try:
            from ...config import get_config
            cfg = get_config()
            api_key = cfg.get("anthropic_api_key")
        except Exception:
            pass
        
        if not api_key:
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None


def _extract_text_from_messages(messages: List[Dict[str, Any]]) -> str:
    """Extract all text content from messages."""
    text_parts = []
    for msg in messages:
        content = msg.get("content", [])
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
    return "\n".join(text_parts)
