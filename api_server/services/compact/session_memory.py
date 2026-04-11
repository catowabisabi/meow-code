"""Session memory compaction implementation."""
from .types import (
    CompactionResult,
    SessionMemoryCompactConfig,
)


sm_compact_config = SessionMemoryCompactConfig(
    min_tokens=10_000,
    min_text_block_messages=5,
    max_tokens=40_000,
)


config_initialized = False


def set_session_memory_compact_config(config: SessionMemoryCompactConfig) -> None:
    global sm_compact_config
    sm_compact_config = config


def get_session_memory_compact_config() -> SessionMemoryCompactConfig:
    return SessionMemoryCompactConfig(
        min_tokens=sm_compact_config.min_tokens,
        min_text_block_messages=sm_compact_config.min_text_block_messages,
        max_tokens=sm_compact_config.max_tokens,
    )


def reset_session_memory_compact_config() -> None:
    global sm_compact_config, config_initialized
    sm_compact_config = SessionMemoryCompactConfig(
        min_tokens=10_000,
        min_text_block_messages=5,
        max_tokens=40_000,
    )
    config_initialized = False


def has_text_blocks(message) -> bool:
    if message.type == "assistant":
        content = message.message.content
        return any(block.type == "text" for block in content)
    if message.type == "user":
        content = message.message.content
        if isinstance(content, str):
            return len(content) > 0
        if isinstance(content, list):
            return any(block.type == "text" for block in content)
    return False


def get_tool_result_ids(message) -> list:
    if message.type != "user":
        return []
    content = message.message.content
    if not isinstance(content, list):
        return []
    return [
        block.tool_use_id
        for block in content
        if block.type == "tool_result"
    ]


def has_tool_use_with_ids(message, tool_use_ids: set) -> bool:
    if message.type != "assistant":
        return False
    content = message.message.content
    if not isinstance(content, list):
        return False
    return any(
        block.type == "tool_use" and block.id in tool_use_ids
        for block in content
    )


def adjust_index_to_preserve_api_invariants(
    messages: list,
    start_index: int,
) -> int:
    if start_index <= 0 or start_index >= len(messages):
        return start_index
    
    adjusted_index = start_index
    
    all_tool_result_ids = []
    for i in range(start_index, len(messages)):
        all_tool_result_ids.extend(get_tool_result_ids(messages[i]))
    
    if all_tool_result_ids:
        tool_use_ids_in_kept_range = set()
        for i in range(adjusted_index, len(messages)):
            msg = messages[i]
            if msg.type == "assistant" and isinstance(msg.message.content, list):
                for block in msg.message.content:
                    if block.type == "tool_use":
                        tool_use_ids_in_kept_range.add(block.id)
        
        needed_tool_use_ids = set(
            id for id in all_tool_result_ids if id not in tool_use_ids_in_kept_range
        )
        
        for i in range(adjusted_index - 1, -1, -1):
            if not needed_tool_use_ids:
                break
            message = messages[i]
            if has_tool_use_with_ids(message, needed_tool_use_ids):
                adjusted_index = i
                if message.type == "assistant" and isinstance(message.message.content, list):
                    for block in message.message.content:
                        if block.type == "tool_use" and block.id in needed_tool_use_ids:
                            needed_tool_use_ids.discard(block.id)
    
    message_ids_in_kept_range = set()
    for i in range(adjusted_index, len(messages)):
        msg = messages[i]
        if msg.type == "assistant" and msg.message.id:
            message_ids_in_kept_range.add(msg.message.id)
    
    for i in range(adjusted_index - 1, -1, -1):
        message = messages[i]
        if (
            message.type == "assistant"
            and message.message.id
            and message.message.id in message_ids_in_kept_range
        ):
            adjusted_index = i
    
    return adjusted_index


def calculate_messages_to_keep_index(
    messages: list,
    last_summarized_index: int,
) -> int:
    if not messages:
        return 0
    
    config = get_session_memory_compact_config()
    
    start_index = last_summarized_index + 1 if last_summarized_index >= 0 else len(messages)
    
    total_tokens = 0
    text_block_message_count = 0
    for i in range(start_index, len(messages)):
        msg = messages[i]
        total_tokens += estimate_message_tokens([msg])
        if has_text_blocks(msg):
            text_block_message_count += 1
    
    if total_tokens >= config.max_tokens:
        return adjust_index_to_preserve_api_invariants(messages, start_index)
    
    if total_tokens >= config.min_tokens and text_block_message_count >= config.min_text_block_messages:
        return adjust_index_to_preserve_api_invariants(messages, start_index)
    
    boundary_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if is_compact_boundary_message(messages[i]):
            boundary_idx = i
            break
    
    floor_idx = boundary_idx + 1 if boundary_idx != -1 else 0
    
    for i in range(start_index - 1, floor_idx - 1, -1):
        if i < 0:
            break
        msg = messages[i]
        msg_tokens = estimate_message_tokens([msg])
        total_tokens += msg_tokens
        if has_text_blocks(msg):
            text_block_message_count += 1
        start_index = i
        
        if total_tokens >= config.max_tokens:
            break
        
        if total_tokens >= config.min_tokens and text_block_message_count >= config.min_text_block_messages:
            break
    
    return adjust_index_to_preserve_api_invariants(messages, start_index)


def is_compact_boundary_message(message) -> bool:
    return message.type == "system" and getattr(message, "is_compact_boundary", False)


def should_use_session_memory_compaction() -> bool:
    return False


async def try_session_memory_compaction(
    messages: list,
    agent_id=None,
    auto_compact_threshold=None,
) -> CompactionResult | None:
    return None


def estimate_message_tokens(messages: list) -> int:
    from .time_based import rough_token_count_estimation
    
    total_tokens = 0
    for message in messages:
        if message.type not in ("user", "assistant"):
            continue
        
        content = message.message.content
        if not isinstance(content, list):
            continue
        
        for block in content:
            if block.type == "text":
                total_tokens += rough_token_count_estimation(block.text)
            elif block.type == "tool_result":
                total_tokens += estimate_tool_result_tokens(block)
            elif block.type in ("image", "document"):
                total_tokens += 2000
            elif block.type == "thinking":
                total_tokens += rough_token_count_estimation(block.thinking)
    
    return total_tokens


def estimate_tool_result_tokens(block) -> int:
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


def merge_session_memories(memories: list[str]) -> str:
    return "\n\n---\n\n".join(memories)


def extract_key_memories(memory: str, max_tokens: int = 5000) -> str:
    lines = memory.split("\n")
    result = []
    current_tokens = 0
    
    for line in lines:
        line_tokens = len(line) // 4
        if current_tokens + line_tokens > max_tokens:
            break
        result.append(line)
        current_tokens += line_tokens
    
    return "\n".join(result)


class SessionMemoryCompactor:
    pass