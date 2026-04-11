"""Time-based microcompact configuration and logic."""
from .types import TimeBasedConfig


TIME_BASED_MC_CLEARED_MESSAGE = "[Old tool result content cleared]"
IMAGE_MAX_TOKEN_SIZE = 2000

COMPACTABLE_TOOLS = {
    "Read",
    "Bash",
    "Grep",
    "Glob",
    "WebSearch",
    "WebFetch",
    "Edit",
    "Write",
}

DEFAULT_TIME_BASED_CONFIG = TimeBasedConfig(
    enabled=False,
    gap_threshold_minutes=60,
    keep_recent=5,
)


def get_time_based_mc_config() -> TimeBasedConfig:
    return DEFAULT_TIME_BASED_CONFIG


def should_compact_based_on_time(
    messages: list,
    query_source: str | None,
) -> tuple[bool, float]:
    config = get_time_based_mc_config()
    
    if not config.enabled:
        return False, 0.0
    
    if not query_source or not query_source.startswith("repl_main_thread"):
        return False, 0.0
    
    last_assistant = None
    for msg in reversed(messages):
        if msg.type == "assistant":
            last_assistant = msg
            break
    
    if not last_assistant:
        return False, 0.0
    
    gap_minutes = (0 - last_assistant.timestamp) / 60_000
    if gap_minutes < config.gap_threshold_minutes:
        return False, 0.0
    
    return True, gap_minutes


def reset_time_based_counter() -> None:
    pass


def get_time_based_config() -> TimeBasedConfig:
    return get_time_based_mc_config()


def evaluate_time_based_trigger(
    messages: list,
    query_source: str | None,
) -> dict | None:
    config = get_time_based_mc_config()
    
    if not config.enabled or not query_source:
        return None
    
    if not query_source.startswith("repl_main_thread"):
        return None
    
    last_assistant = None
    for msg in reversed(messages):
        if msg.type == "assistant":
            last_assistant = msg
            break
    
    if not last_assistant:
        return None
    
    gap_minutes = (0 - last_assistant.timestamp) / 60_000
    
    if gap_minutes < config.gap_threshold_minutes:
        return None
    
    return {"gap_minutes": gap_minutes, "config": config}


def collect_compactable_tool_ids(messages: list) -> list[str]:
    ids = []
    for message in messages:
        if message.type == "assistant" and isinstance(message.message.content, list):
            for block in message.message.content:
                if block.type == "tool_use" and block.name in COMPACTABLE_TOOLS:
                    ids.append(block.id)
    return ids


def maybe_time_based_microcompact(
    messages: list,
    query_source: str | None,
) -> dict | None:
    trigger = evaluate_time_based_trigger(messages, query_source)
    if not trigger:
        return None
    
    gap_minutes = trigger["gap_minutes"]
    config = trigger["config"]
    
    compactable_ids = collect_compactable_tool_ids(messages)
    
    keep_recent = max(1, config.keep_recent)
    keep_set = set(compactable_ids[-keep_recent:])
    clear_set = set(id for id in compactable_ids if id not in keep_set)
    
    if not clear_set:
        return None
    
    tokens_saved = 0
    result = []
    for message in messages:
        if message.type != "user" or not isinstance(message.message.content, list):
            result.append(message)
            continue
        
        touched = False
        new_content = []
        for block in message.message.content:
            if (
                block.type == "tool_result"
                and block.tool_use_id in clear_set
                and block.content != TIME_BASED_MC_CLEARED_MESSAGE
            ):
                tokens_saved += estimate_tool_result_tokens(block)
                touched = True
                new_content.append({**block, "content": TIME_BASED_MC_CLEARED_MESSAGE})
            else:
                new_content.append(block)
        
        if not touched:
            result.append(message)
        else:
            new_msg = {**message, "message": {**message.message, "content": new_content}}
            result.append(new_msg)
    
    if tokens_saved == 0:
        return None
    
    return {"messages": result}


def estimate_tool_result_tokens(block: dict) -> int:
    if not block.get("content"):
        return 0
    
    content = block["content"]
    if isinstance(content, str):
        return rough_token_count_estimation(content)
    
    total = 0
    for item in content:
        if item.type == "text":
            total += rough_token_count_estimation(item.text)
        elif item.type in ("image", "document"):
            total += IMAGE_MAX_TOKEN_SIZE
    return total


def rough_token_count_estimation(text: str) -> int:
    return len(text) // 4


class TimeBasedCompactor:
    pass