"""Micro compaction - lightweight compaction before API calls."""
from .types import MicroCompactResult, PendingCacheEdits
from .time_based import (
    TIME_BASED_MC_CLEARED_MESSAGE,
    evaluate_time_based_trigger,
    maybe_time_based_microcompact,
    collect_compactable_tool_ids,
)
from .warning_state import suppress_compact_warning, clear_compact_warning_suppression


cached_mc_module = None
cached_mc_state = None
pending_cache_edits = None


def get_cached_mc_module():
    """Get the cached microcompact module."""
    return cached_mc_module


def ensure_cached_mc_state():
    """Ensure cached_mc_state is initialized."""
    global cached_mc_state
    if cached_mc_state is None:
        cached_mc_state = {
            "tools_sent_to_api": False,
            "last_compact_time": None,
            "pinned_edits": [],
        }


def consume_pending_cache_edits() -> PendingCacheEdits | None:
    global pending_cache_edits
    edits = pending_cache_edits
    pending_cache_edits = None
    return edits


def get_pinned_cache_edits() -> list:
    if not cached_mc_state:
        return []
    return cached_mc_state.get("pinned_edits", [])


def pin_cache_edits(user_message_index: int, block: dict) -> None:
    global cached_mc_state
    if cached_mc_state:
        if "pinned_edits" not in cached_mc_state:
            cached_mc_state["pinned_edits"] = []
        cached_mc_state["pinned_edits"].append({
            "user_message_index": user_message_index,
            "block": block,
        })


def mark_tools_sent_to_api_state() -> None:
    """Mark that tools have been sent to the API."""
    global cached_mc_state
    if cached_mc_state is not None:
        cached_mc_state["tools_sent_to_api"] = True


def reset_microcompact_state() -> None:
    """Reset all microcompact state."""
    global cached_mc_state, cached_mc_module, pending_cache_edits
    cached_mc_module = None
    cached_mc_state = None
    pending_cache_edits = None


def estimate_message_tokens(messages: list) -> int:
    from .time_based import rough_token_count_estimation, IMAGE_MAX_TOKEN_SIZE
    
    total_tokens = 0
    for message in messages:
        if message.type not in ("user", "assistant"):
            continue
        
        if not isinstance(message.message.content, list):
            continue
        
        for block in message.message.content:
            if block.type == "text":
                total_tokens += rough_token_count_estimation(block.text)
            elif block.type == "tool_result":
                total_tokens += calculate_tool_result_tokens(block)
            elif block.type in ("image", "document"):
                total_tokens += IMAGE_MAX_TOKEN_SIZE
            elif block.type == "thinking":
                total_tokens += rough_token_count_estimation(block.thinking)
            elif block.type == "redacted_thinking":
                total_tokens += rough_token_count_estimation(block.get("data", ""))
            elif block.type == "tool_use":
                name = block.name or ""
                input_str = str(block.input or {})
                total_tokens += rough_token_count_estimation(name + input_str)
    
    return int(total_tokens * (4 / 3))


def calculate_tool_result_tokens(block) -> int:
    from .time_based import rough_token_count_estimation, IMAGE_MAX_TOKEN_SIZE
    
    if not block.content:
        return 0
    
    if isinstance(block.content, str):
        return rough_token_count_estimation(block.content)
    
    total = 0
    for item in block.content:
        if item.type == "text":
            total += rough_token_count_estimation(item.text)
        elif item.type in ("image", "document"):
            total += IMAGE_MAX_TOKEN_SIZE
    return total


def is_main_thread_source(query_source) -> bool:
    return not query_source or query_source.startswith("repl_main_thread")


async def microcompact_messages(
    messages: list,
    tool_use_context=None,
    query_source=None,
) -> MicroCompactResult:
    clear_compact_warning_suppression()
    
    time_based_result = maybe_time_based_microcompact(messages, query_source)
    if time_based_result:
        return MicroCompactResult(messages=time_based_result["messages"])
    
    return MicroCompactResult(messages=messages)


def strip_images_from_messages(messages: list) -> list:
    return [
        strip_images_from_message(msg) if msg.type == "user" else msg
        for msg in messages
    ]


def strip_images_from_message(message) -> dict:
    if message.type != "user":
        return message
    
    content = message.message.content
    if not isinstance(content, list):
        return message
    
    has_media_block = False
    new_content = []
    
    for block in content:
        if block.type == "image":
            has_media_block = True
            new_content.append({"type": "text", "text": "[image]"})
        elif block.type == "document":
            has_media_block = True
            new_content.append({"type": "text", "text": "[document]"})
        elif block.type == "tool_result" and isinstance(block.content, list):
            tool_has_media = False
            new_tool_content = []
            for item in block.content:
                if item.type == "image":
                    tool_has_media = True
                    new_tool_content.append({"type": "text", "text": "[image]"})
                elif item.type == "document":
                    tool_has_media = True
                    new_tool_content.append({"type": "text", "text": "[document]"})
                else:
                    new_tool_content.append(item)
            
            if tool_has_media:
                has_media_block = True
                new_content.append({**block, "content": new_tool_content})
            else:
                new_content.append(block)
        else:
            new_content.append(block)
    
    if not has_media_block:
        return message
    
    return {
        **message,
        "message": {**message.message, "content": new_content},
    }


def strip_reinjected_attachments(messages: list) -> list:
    return messages


def group_similar_messages(messages: list) -> list[list]:
    groups = []
    current_group = []
    last_assistant_id = None
    
    for msg in messages:
        if (
            msg.type == "assistant"
            and msg.message.id != last_assistant_id
            and current_group
        ):
            groups.append(current_group)
            current_group = [msg]
        else:
            current_group.append(msg)
        
        if msg.type == "assistant":
            last_assistant_id = msg.message.id
    
    if current_group:
        groups.append(current_group)
    
    return groups


class MicroCompactor:
    def __init__(self):
        self.pending_cache_edits = None
    
    async def compact(self, messages: list, query_source: str = None) -> MicroCompactResult:
        return await microcompact_messages(messages, None, query_source)
    
    def api_micro_compact(self, messages: list, options: dict = None) -> dict:
        options = options or {}
        
        strategies = []
        
        has_thinking = options.get("has_thinking", False)
        is_redact_thinking_active = options.get("is_redact_thinking_active", False)
        clear_all_thinking = options.get("clear_all_thinking", False)
        
        if has_thinking and not is_redact_thinking_active:
            keep = {"type": "thinking_turns", "value": 1} if clear_all_thinking else "all"
            strategies.append({"type": "clear_thinking_20251015", "keep": keep})
        
        result = {"messages": messages}
        if strategies:
            result["context_management"] = {"edits": strategies}
        
        return result