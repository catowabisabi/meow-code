"""Auto compaction - automatic context reduction when context window fills."""
from .types import (
    AutoCompactThreshold,
    AutoCompactTrackingState,
    CompactionResult,
    RecompactionInfo,
    TokenWarningState,
    AUTOCOMPACT_BUFFER_TOKENS,
    WARNING_THRESHOLD_BUFFER_TOKENS,
    ERROR_THRESHOLD_BUFFER_TOKENS,
    MANUAL_COMPACT_BUFFER_TOKENS,
    MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES,
)


MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000


auto_compact_enabled = True
auto_compact_window_override = None


def get_effective_context_window_size(model: str) -> int:
    reserved = min(20000, MAX_OUTPUT_TOKENS_FOR_SUMMARY)
    context_window = 200000
    
    if auto_compact_window_override:
        context_window = min(context_window, auto_compact_window_override)
    
    return context_window - reserved


def get_auto_compact_threshold(model: str) -> int:
    effective = get_effective_context_window_size(model)
    return effective - AUTOCOMPACT_BUFFER_TOKENS


def calculate_token_warning_state(
    token_usage: int,
    model: str,
) -> TokenWarningState:
    auto_threshold = get_auto_compact_threshold(model)
    threshold = auto_threshold if is_auto_compact_enabled() else get_effective_context_window_size(model)
    
    percent_left = max(0, round(((threshold - token_usage) / threshold) * 100))
    
    warning_threshold = threshold - WARNING_THRESHOLD_BUFFER_TOKENS
    error_threshold = threshold - ERROR_THRESHOLD_BUFFER_TOKENS
    
    return TokenWarningState(
        percent_left=percent_left,
        is_above_warning_threshold=token_usage >= warning_threshold,
        is_above_error_threshold=token_usage >= error_threshold,
        is_above_auto_compact_threshold=is_auto_compact_enabled() and token_usage >= auto_threshold,
        is_at_blocking_limit=token_usage >= (threshold - MANUAL_COMPACT_BUFFER_TOKENS),
    )


def is_auto_compact_enabled() -> bool:
    return auto_compact_enabled


def set_auto_compact_enabled(enabled: bool) -> None:
    global auto_compact_enabled
    auto_compact_enabled = enabled


async def should_auto_compact(
    messages: list,
    model: str,
    query_source: str = None,
    snip_tokens_freed: int = 0,
) -> bool:
    if query_source in ("session_memory", "compact"):
        return False
    
    if not is_auto_compact_enabled():
        return False
    
    token_count = estimate_token_count(messages) - snip_tokens_freed
    threshold = get_auto_compact_threshold(model)
    
    return token_count >= threshold


def estimate_token_count(messages: list) -> int:
    total = 0
    for msg in messages:
        if hasattr(msg, 'message') and hasattr(msg.message, 'content'):
            content = msg.message.content
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total += len(block.get("text", "")) // 4
    return total


async def auto_compact_if_needed(
    messages: list,
    tool_use_context,
    cache_safe_params: dict,
    query_source: str = None,
    tracking: AutoCompactTrackingState = None,
    snip_tokens_freed: int = 0,
) -> dict:
    global MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES
    
    if tracking and tracking.consecutive_failures >= MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
        return {"was_compacted": False}
    
    from .compact import compact_conversation
    
    model = getattr(tool_use_context, 'options', {}).get('main_loop_model', 'claude-3-5-sonnet-20241022')
    
    should_compact = await should_auto_compact(messages, model, query_source, snip_tokens_freed)
    
    if not should_compact:
        return {"was_compacted": False}
    
    recompaction_info = RecompactionInfo(
        is_recompaction_in_chain=tracking.compacted if tracking else False,
        turns_since_previous_compact=tracking.turn_counter if tracking else -1,
        previous_compact_turn_id=getattr(tracking, 'turn_id', None),
        auto_compact_threshold=get_auto_compact_threshold(model),
        query_source=query_source,
    )
    
    try:
        result = await compact_conversation(
            messages=messages,
            context=tool_use_context,
            cache_safe_params=cache_safe_params,
            suppress_follow_up_questions=True,
            custom_instructions=None,
            is_auto_compact=True,
            recompaction_info=recompaction_info,
        )
        
        from .post_cleanup import run_post_compact_cleanup
        run_post_compact_cleanup(query_source)
        
        return {
            "was_compacted": True,
            "compaction_result": result,
            "consecutive_failures": 0,
        }
    except Exception as error:
        consecutive_failures = (tracking.consecutive_failures if tracking else 0) + 1
        return {
            "was_compacted": False,
            "consecutive_failures": consecutive_failures,
        }


def setup_auto_compact(config: dict = None) -> None:
    global auto_compact_window_override
    
    if config:
        if 'enabled' in config:
            set_auto_compact_enabled(config['enabled'])
        if 'window' in config:
            auto_compact_window_override = config['window']


def check_auto_compact_trigger(
    messages: list,
    model: str,
    query_source: str = None,
) -> bool:
    return is_auto_compact_enabled() and estimate_token_count(messages) >= get_auto_compact_threshold(model)


def cancel_auto_compact() -> None:
    set_auto_compact_enabled(False)


class AutoCompactor:
    def __init__(self):
        self.tracking_state = None
    
    async def try_compact(
        self,
        messages: list,
        tool_use_context,
        cache_safe_params: dict,
        query_source: str = None,
    ) -> dict:
        return await auto_compact_if_needed(
            messages=messages,
            tool_use_context=tool_use_context,
            cache_safe_params=cache_safe_params,
            query_source=query_source,
            tracking=self.tracking_state,
        )
    
    def setup(self, config: dict = None) -> None:
        setup_auto_compact(config)
    
    def check_trigger(self, messages: list, model: str, query_source: str = None) -> bool:
        return check_auto_compact_trigger(messages, model, query_source)
    
    def cancel(self) -> None:
        cancel_auto_compact()