"""Main compaction service - compresses conversation history when context fills."""
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from .types import (
    CompactionResult,
    CompactionUsage,
    CompactConfig,
    CompactMetadata,
    CompactStrategy,
    ERROR_MESSAGE_INCOMPLETE_RESPONSE,
    ERROR_MESSAGE_NOT_ENOUGH_MESSAGES,
    ERROR_MESSAGE_PROMPT_TOO_LONG,
    ERROR_MESSAGE_USER_ABORT,
    PartialCompactDirection,
    PostCompactCleanupResult,
    PreservedSegment,
    RecompactionInfo,
    SummarizeMetadata,
    POST_COMPACT_MAX_FILES_TO_RESTORE,
    POST_COMPACT_MAX_TOKENS_PER_FILE,
    POST_COMPACT_MAX_TOKENS_PER_SKILL,
    POST_COMPACT_SKILLS_TOKEN_BUDGET,
    POST_COMPACT_TOKEN_BUDGET,
)
from .prompt import (
    format_compact_summary,
    get_compact_prompt,
    get_compact_user_summary_message,
    get_partial_compact_prompt,
)
from .grouping import group_messages_by_api_round, truncate_head_for_ptl_retry
from .micro_compact import (
    estimate_message_tokens,
    strip_images_from_messages,
    strip_reinjected_attachments,
)
from .post_cleanup import run_post_compact_cleanup
from .session_memory import try_session_memory_compaction
from .warning_state import suppress_compact_warning, clear_compact_warning_suppression
from .auto_compact import get_auto_compact_threshold


MAX_COMPACT_STREAMING_RETRIES = 2

# Boundary markers for compacted sections
MARKER_COMPACT_BOUNDARY = "^^^ COMPACTED ^^^"
MARKER_SUMMARY_START = "=== Session Summary ==="
MARKER_SUMMARY_END = "=== End Summary ==="

# Skill truncation marker
SKILL_TRUNCATION_MARKER = "\n\n[... skill content truncated for compaction; use Read on the skill path if you need the full text]"

# Prompt cache sharing experiment flag (3P default: true)
PROMPT_CACHE_SHARING_ENABLED = True
# Streaming retry experiment flag
STREAMING_RETRY_ENABLED = False


def generate_uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class CompactionBudget:
    """Token budget management during compaction."""
    max_tokens: int
    used_tokens: int = 0
    buffer_tokens: int = 500
    
    def can_compact(self, additional_tokens: int) -> bool:
        """Check if we can afford to add more tokens."""
        return (self.used_tokens + additional_tokens + self.buffer_tokens) <= self.max_tokens
    
    def reserve(self, tokens: int) -> None:
        """Reserve tokens for an upcoming allocation."""
        self.used_tokens += tokens
    
    def release(self, tokens: int) -> None:
        """Release previously reserved tokens."""
        self.used_tokens = max(0, self.used_tokens - tokens)
    
    def remaining(self) -> int:
        """Get remaining tokens in budget."""
        return max(0, self.max_tokens - self.used_tokens - self.buffer_tokens)


# Preservation reasons for selective compaction
PRESERVE_REASONS = {
    "user_clarification": True,
    "tool_error": True,
    "decision_point": True,
    "important_reply": True,
}


def should_preserve_message(message: dict, reason: str) -> bool:
    """Check if message should be preserved during compaction.
    
    Messages are preserved if they:
    - Contain user clarifications
    - Contain tool errors
    - Represent decision points
    - Are important replies
    """
    return PRESERVE_REASONS.get(reason, False)


def add_compact_boundary(messages: list) -> list:
    """Add visual boundary markers around compacted section."""
    boundary = {
        "type": "system",
        "is_compact_boundary": True,
        "uuid": generate_uuid(),
        "timestamp": 0,
        "compact_metadata": {
            "mode": "auto",
        },
        "content": MARKER_COMPACT_BOUNDARY,
    }
    return [boundary] + messages


def build_post_compact_messages(result: CompactionResult) -> list:
    """Build the base post-compact messages array from a CompactionResult.
    
    Ensures consistent ordering across all compaction paths:
    Order: boundaryMarker, summaryMessages, messagesToKeep, attachments, hookResults
    """
    return [
        result.boundary_marker,
        *result.summary_messages,
        *(result.messages_to_keep or []),
        *result.attachments,
        *result.hook_results,
    ]


def annotate_boundary_with_preserved_segment(
    boundary: dict,
    anchor_uuid: str,
    messages_to_keep: list = None,
) -> dict:
    """Annotate a compact boundary with relink metadata for messagesToKeep.
    
    Preserved messages keep their original parentUuids on disk (dedup-skipped);
    the loader uses this to patch head→anchor and anchor's-other-children→tail.
    
    anchorUuid = what sits immediately before keep[0] in the desired chain:
      - suffix-preserving (reactive/session-memory): last summary message
      - prefix-preserving (partial compact): the boundary itself
    """
    keep = messages_to_keep or []
    if not keep:
        return boundary
    
    return {
        **boundary,
        "compact_metadata": {
            **boundary.get("compact_metadata", {}),
            "preserved_segment": {
                "head_uuid": keep[0].get("uuid", ""),
                "anchor_uuid": anchor_uuid,
                "tail_uuid": keep[-1].get("uuid", ""),
            },
        },
    }


def merge_hook_instructions(
    user_instructions: str = None,
    hook_instructions: str = None,
) -> str | None:
    """Merges user-supplied custom instructions with hook-provided instructions.
    
    User instructions come first; hook instructions are appended.
    Empty strings normalize to undefined.
    """
    if not hook_instructions:
        return user_instructions or None
    if not user_instructions:
        return hook_instructions
    return f"{user_instructions}\n\n{hook_instructions}"


def create_compact_boundary_message(
    mode: str,
    pre_compact_token_count: int,
    last_message_uuid: str = None,
    user_feedback: str = None,
    messages_summarized: int = None,
) -> dict:
    """Create a compact boundary system message."""
    metadata = {
        "mode": mode,
        "pre_compact_token_count": pre_compact_token_count,
    }
    
    if last_message_uuid:
        metadata["last_message_uuid"] = last_message_uuid
    if user_feedback:
        metadata["user_feedback"] = user_feedback
    if messages_summarized is not None:
        metadata["messages_summarized"] = messages_summarized
    
    return {
        "type": "system",
        "is_compact_boundary": True,
        "uuid": generate_uuid(),
        "timestamp": 0,
        "compact_metadata": metadata,
    }


def create_compact_can_use_tool() -> Callable:
    """Create a can_use_tool function that denies tool usage during compaction."""
    async def can_use_tool():
        return {
            "behavior": "deny",
            "message": "Tool use is not allowed during compaction",
            "decision_reason": {
                "type": "other",
                "reason": "compaction agent should only produce text summary",
            },
        }
    return can_use_tool


async def execute_pre_compact_hooks(
    trigger: str,
    custom_instructions: str = None,
    signal=None,
) -> dict:
    """Execute pre-compact hooks."""
    # Placeholder for hook execution - actual implementation would call hooks
    return {
        "new_custom_instructions": None,
        "user_display_message": None,
    }


async def execute_post_compact_hooks(
    trigger: str,
    compact_summary: str,
    signal=None,
) -> dict:
    """Execute post-compact hooks."""
    # Placeholder for hook execution - actual implementation would call hooks
    return {
        "user_display_message": None,
    }


async def process_session_start_hooks(
    trigger: str,
    model: str = None,
) -> list:
    """Process session start hooks after successful compaction."""
    # Placeholder for session start hooks
    return []


def log_event(event_name: str, params: dict = None) -> None:
    """Log analytics event."""
    # Placeholder for analytics logging
    pass


def log_error(error: Exception) -> None:
    """Log error."""
    # Placeholder for error logging
    pass


def log_for_debugging(message: str, level: str = "info") -> None:
    """Log debug message."""
    # Placeholder for debug logging
    pass


async def compact_conversation(
    messages: list,
    context,
    cache_safe_params: dict,
    suppress_follow_up_questions: bool = False,
    custom_instructions: str = None,
    is_auto_compact: bool = False,
    recompaction_info: RecompactionInfo = None,
) -> CompactionResult:
    """Compact a conversation by summarizing older messages and preserving recent history.
    
    Creates a compact version of a conversation by:
    1. Executing pre-compact hooks
    2. Generating a summary via AI of older messages
    3. Creating boundary markers and summary messages
    4. Restoring important file/attachment context
    5. Executing post-compact hooks
    """
    if not messages:
        raise ValueError(ERROR_MESSAGE_NOT_ENOUGH_MESSAGES)
    
    pre_compact_token_count = estimate_message_tokens(messages)
    
    # Clear compact warning suppression
    clear_compact_warning_suppression()
    
    # Execute PreCompact hooks
    hook_result = await execute_pre_compact_hooks(
        trigger="auto" if is_auto_compact else "manual",
        custom_instructions=custom_instructions,
        signal=getattr(context, 'abort_controller', None),
    )
    
    custom_instructions = merge_hook_instructions(
        custom_instructions,
        hook_result.get("new_custom_instructions"),
    )
    
    user_display_message = hook_result.get("user_display_message")
    
    # Get compact prompt
    compact_prompt = get_compact_prompt(custom_instructions)
    summary_request = {
        "type": "user",
        "message": {"content": compact_prompt},
        "uuid": generate_uuid(),
        "timestamp": 0,
    }
    
    messages_to_summarize = messages
    retry_cache_safe_params = cache_safe_params
    summary_response = None
    summary_text = None
    ptl_attempts = 0
    
    for _ in range(MAX_COMPACT_STREAMING_RETRIES + 1):
        summary_response = await stream_compact_summary(
            messages=messages_to_summarize,
            summary_request=summary_request,
            context=context,
            pre_compact_token_count=pre_compact_token_count,
            cache_safe_params=retry_cache_safe_params,
        )
        
        summary_text = extract_text_from_response(summary_response)
        
        if summary_text and not summary_text.startswith(ERROR_MESSAGE_PROMPT_TOO_LONG):
            break
        
        # CC-1180: compact request hit prompt-too-long, truncate oldest groups
        ptl_attempts += 1
        truncated = truncate_head_for_ptl_retry(messages_to_summarize, summary_response)
        
        if not truncated:
            log_event("tengu_compact_failed", {
                "reason": "prompt_too_long",
                "pre_compact_token_count": pre_compact_token_count,
                "ptl_attempts": ptl_attempts,
            })
            raise ValueError(ERROR_MESSAGE_PROMPT_TOO_LONG)
        
        log_event("tengu_compact_ptl_retry", {
            "attempt": ptl_attempts,
            "dropped_messages": len(messages_to_summarize) - len(truncated),
            "remaining_messages": len(truncated),
        })
        
        messages_to_summarize = truncated
        retry_cache_safe_params = {
            **retry_cache_safe_params,
            "fork_context_messages": truncated,
        }
    
    if not summary_text:
        log_event("tengu_compact_failed", {
            "reason": "no_summary",
            "pre_compact_token_count": pre_compact_token_count,
        })
        raise ValueError(
            "Failed to generate conversation summary - response did not contain valid text content"
        )
    
    # Store the current file state before clearing
    pre_compact_read_file_state = cache_to_object(context.read_file_state)
    
    # Clear the cache
    context.read_file_state.clear()
    if context.loaded_nested_memory_paths:
        context.loaded_nested_memory_paths.clear()
    
    # Create post-compact file attachments
    post_compact_file_attachments = await create_post_compact_file_attachments(
        pre_compact_read_file_state,
        context,
        POST_COMPACT_MAX_FILES_TO_RESTORE,
        [],
    )
    
    # Create async agent attachments
    async_agent_attachments = await create_async_agent_attachments_if_needed(context)
    
    post_compact_file_attachments = [
        *post_compact_file_attachments,
        *async_agent_attachments,
    ]
    
    # Create plan attachment if needed
    plan_attachment = create_plan_attachment_if_needed(context.agent_id)
    if plan_attachment:
        post_compact_file_attachments.append(plan_attachment)
    
    # Create plan mode attachment if needed
    plan_mode_attachment = await create_plan_mode_attachment_if_needed(context)
    if plan_mode_attachment:
        post_compact_file_attachments.append(plan_mode_attachment)
    
    # Create skill attachment if skills were invoked
    skill_attachment = create_skill_attachment_if_needed(context.agent_id)
    if skill_attachment:
        post_compact_file_attachments.append(skill_attachment)
    
    # Add deferred tools delta attachments
    for att in get_deferred_tools_delta_attachment(context.options.tools, context.options.main_loop_model, []):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    # Add agent listing delta attachments
    for att in get_agent_listing_delta_attachment(context, []):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    # Add MCP instructions delta attachments
    for att in get_mcp_instructions_delta_attachment(
        context.options.mcp_clients,
        context.options.tools,
        context.options.main_loop_model,
        [],
    ):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    # Process session start hooks
    hook_messages = await process_session_start_hooks("compact", {
        "model": context.options.main_loop_model,
    })
    
    # Create the compact boundary marker
    boundary_marker = create_compact_boundary_message(
        "auto" if is_auto_compact else "manual",
        pre_compact_token_count,
        messages[-1].get("uuid") if messages else None,
    )
    
    # Carry loaded-tool state
    pre_compact_discovered = extract_discovered_tool_names(messages)
    if pre_compact_discovered:
        boundary_marker["compact_metadata"]["pre_compact_discovered_tools"] = sorted(
            list(pre_compact_discovered)
        )
    
    # Get transcript path
    transcript_path = get_transcript_path()
    
    # Create summary messages
    summary_messages = [{
        "type": "user",
        "is_compact_summary": True,
        "is_visible_in_transcript_only": True,
        "uuid": generate_uuid(),
        "timestamp": 0,
        "message": {
            "content": get_compact_user_summary_message(
                summary_text,
                suppress_follow_up_questions,
                transcript_path,
            ),
        },
    }]
    
    # Calculate token counts
    true_post_compact_token_count = estimate_message_tokens([
        boundary_marker,
        *summary_messages,
        *post_compact_file_attachments,
        *hook_messages,
    ])
    
    # Extract compaction usage
    compaction_usage = extract_compaction_usage(summary_response)
    
    # Log event
    query_source = None
    if recompaction_info:
        query_source = recompaction_info.query_source
    elif context.options:
        query_source = context.options.query_source
    
    log_event("tengu_compact", {
        "pre_compact_token_count": pre_compact_token_count,
        "post_compact_token_count": compaction_usage.total_tokens if compaction_usage else 0,
        "true_post_compact_token_count": true_post_compact_token_count,
        "auto_compact_threshold": recompaction_info.auto_compact_threshold if recompaction_info else -1,
        "is_auto_compact": is_auto_compact,
        "query_source": query_source or "unknown",
    })
    
    # Reset cache read baseline for prompt cache break detection
    notify_compaction(context.options.query_source if context.options else "compact", context.agent_id)
    
    # Re-append session metadata
    re_append_session_metadata()
    
    # Write transcript segment if enabled
    write_session_transcript_segment(messages)
    
    # Execute post-compact hooks
    post_compact_hook_result = await execute_post_compact_hooks(
        trigger="auto" if is_auto_compact else "manual",
        compact_summary=summary_text,
        signal=getattr(context, 'abort_controller', None),
    )
    
    combined_user_display_message = user_display_message
    if post_compact_hook_result.get("user_display_message"):
        if combined_user_display_message:
            combined_user_display_message = (
                f"{combined_user_display_message}\n"
                f"{post_compact_hook_result['user_display_message']}"
            )
        else:
            combined_user_display_message = post_compact_hook_result["user_display_message"]
    
    return CompactionResult(
        boundary_marker=boundary_marker,
        summary_messages=summary_messages,
        attachments=post_compact_file_attachments,
        hook_results=hook_messages,
        user_display_message=combined_user_display_message,
        pre_compact_token_count=pre_compact_token_count,
        post_compact_token_count=compaction_usage.total_tokens if compaction_usage else 0,
        true_post_compact_token_count=true_post_compact_token_count,
        compaction_usage=compaction_usage,
    )


async def partial_compact_conversation(
    all_messages: list,
    pivot_index: int,
    context,
    cache_safe_params: dict,
    user_feedback: str = None,
    direction: PartialCompactDirection = PartialCompactDirection.FROM,
) -> CompactionResult:
    """Perform partial compaction around the selected message index.
    
    Direction 'from': summarizes messages after the index, keeps earlier ones.
      Prompt cache for kept (earlier) messages is preserved.
    Direction 'up_to': summarizes messages before the index, keeps later ones.
      Prompt cache is invalidated since the summary precedes the kept messages.
    """
    messages_to_summarize = (
        all_messages[:pivot_index] if direction == PartialCompactDirection.UP_TO
        else all_messages[pivot_index:]
    )
    
    # Filter messages to keep
    messages_to_keep = (
        all_messages[pivot_index:]
        if direction == PartialCompactDirection.UP_TO
        else all_messages[:pivot_index]
    )
    
    messages_to_keep = [
        m for m in messages_to_keep
        if m.get("type") != "progress"
        and not m.get("is_compact_boundary", False)
        and not (m.get("type") == "user" and m.get("is_compact_summary", False))
    ]
    
    if not messages_to_summarize:
        raise ValueError(
            "Nothing to summarize before the selected message."
            if direction == PartialCompactDirection.UP_TO
            else "Nothing to summarize after the selected message."
        )
    
    pre_compact_token_count = estimate_message_tokens(all_messages)
    
    # Execute pre-compact hooks
    hook_result = await execute_pre_compact_hooks(
        trigger="manual",
        custom_instructions=None,
        signal=getattr(context, 'abort_controller', None),
    )
    
    # Merge hook instructions with user feedback
    custom_instructions = None
    if hook_result.get("new_custom_instructions") and user_feedback:
        custom_instructions = (
            f"{hook_result['new_custom_instructions']}\n\nUser context: {user_feedback}"
        )
    elif hook_result.get("new_custom_instructions"):
        custom_instructions = hook_result["new_custom_instructions"]
    elif user_feedback:
        custom_instructions = f"User context: {user_feedback}"
    
    # Get partial compact prompt
    compact_prompt = get_partial_compact_prompt(custom_instructions, direction)
    summary_request = {
        "type": "user",
        "message": {"content": compact_prompt},
        "uuid": generate_uuid(),
        "timestamp": 0,
    }
    
    # Determine which messages to send to API
    api_messages = (
        all_messages if direction == PartialCompactDirection.FROM
        else messages_to_summarize
    )
    retry_cache_safe_params = (
        {**cache_safe_params, "fork_context_messages": messages_to_summarize}
        if direction == PartialCompactDirection.UP_TO
        else cache_safe_params
    )
    
    summary_response = await stream_compact_summary(
        messages=api_messages,
        summary_request=summary_request,
        context=context,
        pre_compact_token_count=pre_compact_token_count,
        cache_safe_params=retry_cache_safe_params,
    )
    
    summary_text = extract_text_from_response(summary_response)
    
    if not summary_text:
        log_event("tengu_partial_compact_failed", {
            "reason": "no_summary",
            "pre_compact_token_count": pre_compact_token_count,
            "direction": direction.value,
        })
        raise ValueError(
            "Failed to generate conversation summary - response did not contain valid text content"
        )
    
    # Store file state and clear cache
    pre_compact_read_file_state = cache_to_object(context.read_file_state)
    context.read_file_state.clear()
    if context.loaded_nested_memory_paths:
        context.loaded_nested_memory_paths.clear()
    
    # Create post-compact attachments
    file_attachments = await create_post_compact_file_attachments(
        pre_compact_read_file_state,
        context,
        POST_COMPACT_MAX_FILES_TO_RESTORE,
        messages_to_keep,
    )
    async_agent_attachments = await create_async_agent_attachments_if_needed(context)
    
    post_compact_file_attachments = [*file_attachments, *async_agent_attachments]
    
    # Add plan attachment
    plan_attachment = create_plan_attachment_if_needed(context.agent_id)
    if plan_attachment:
        post_compact_file_attachments.append(plan_attachment)
    
    # Add plan mode attachment
    plan_mode_attachment = await create_plan_mode_attachment_if_needed(context)
    if plan_mode_attachment:
        post_compact_file_attachments.append(plan_mode_attachment)
    
    # Add skill attachment
    skill_attachment = create_skill_attachment_if_needed(context.agent_id)
    if skill_attachment:
        post_compact_file_attachments.append(skill_attachment)
    
    # Re-announce deferred tools for messages to keep
    for att in get_deferred_tools_delta_attachment(
        context.options.tools,
        context.options.main_loop_model,
        messages_to_keep,
    ):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    for att in get_agent_listing_delta_attachment(context, messages_to_keep):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    for att in get_mcp_instructions_delta_attachment(
        context.options.mcp_clients,
        context.options.tools,
        context.options.main_loop_model,
        messages_to_keep,
    ):
        post_compact_file_attachments.append(create_attachment_message(att))
    
    # Process session start hooks
    hook_messages = await process_session_start_hooks("compact", {
        "model": context.options.main_loop_model,
    })
    
    # Calculate token counts
    post_compact_token_count = estimate_message_tokens([summary_response]) if summary_response else 0
    compaction_usage = extract_compaction_usage(summary_response)
    
    log_event("tengu_partial_compact", {
        "pre_compact_token_count": pre_compact_token_count,
        "post_compact_token_count": post_compact_token_count,
        "messages_kept": len(messages_to_keep),
        "messages_summarized": len(messages_to_summarize),
        "direction": direction.value,
        "has_user_feedback": bool(user_feedback),
    })
    
    # Find last pre-compact UUID
    if direction == PartialCompactDirection.UP_TO:
        last_pre_compact_uuid = None
        for msg in reversed(all_messages[:pivot_index]):
            if msg.get("type") != "progress":
                last_pre_compact_uuid = msg.get("uuid")
                break
    else:
        last_pre_compact_uuid = messages_to_keep[-1].get("uuid") if messages_to_keep else None
    
    boundary_marker = create_compact_boundary_message(
        "manual",
        pre_compact_token_count,
        last_pre_compact_uuid,
        user_feedback,
        len(messages_to_summarize),
    )
    
    # Carry discovered tools
    pre_compact_discovered = extract_discovered_tool_names(all_messages)
    if pre_compact_discovered:
        boundary_marker["compact_metadata"]["pre_compact_discovered_tools"] = sorted(
            list(pre_compact_discovered)
        )
    
    transcript_path = get_transcript_path()
    
    # Create summary messages
    summarize_metadata = None
    if messages_to_keep:
        summarize_metadata = {
            "messages_summarized": len(messages_to_summarize),
            "user_context": user_feedback,
            "direction": direction,
        }
    
    summary_messages = [{
        "type": "user",
        "is_compact_summary": True,
        "uuid": generate_uuid(),
        "timestamp": 0,
        "message": {
            "content": get_compact_user_summary_message(summary_text, False, transcript_path),
            **({"summarize_metadata": summarize_metadata} if summarize_metadata else {}),
        },
    }]
    
    # Notify cache break detection
    notify_compaction(context.options.query_source if context.options else "compact", context.agent_id)
    
    # Re-append session metadata
    re_append_session_metadata()
    
    # Write transcript segment
    write_session_transcript_segment(messages_to_summarize)
    
    # Execute post-compact hooks
    post_compact_hook_result = await execute_post_compact_hooks(
        trigger="manual",
        compact_summary=summary_text,
        signal=getattr(context, 'abort_controller', None),
    )
    
    # Determine anchor UUID
    anchor_uuid = (
        summary_messages[-1].get("uuid") if direction == PartialCompactDirection.UP_TO
        else boundary_marker.get("uuid")
    )
    
    return CompactionResult(
        boundary_marker=annotate_boundary_with_preserved_segment(
            boundary_marker,
            anchor_uuid,
            messages_to_keep,
        ),
        summary_messages=summary_messages,
        messages_to_keep=messages_to_keep,
        attachments=post_compact_file_attachments,
        hook_results=hook_messages,
        user_display_message=post_compact_hook_result.get("user_display_message"),
        pre_compact_token_count=pre_compact_token_count,
        post_compact_token_count=post_compact_token_count,
        compaction_usage=compaction_usage,
    )


async def stream_compact_summary(
    messages: list,
    summary_request: dict,
    context,
    pre_compact_token_count: int,
    cache_safe_params: dict,
) -> dict:
    """Stream summary from compact conversation using forked agent or regular API.
    
    When prompt cache sharing is enabled, uses forked agent to reuse the main
    conversation's cached prefix. Falls back to regular streaming path on failure.
    """
    # Send keep-alive signals during compaction to prevent remote session
    # WebSocket idle timeouts from dropping bridge connections.
    activity_interval = None  # Would set up interval for session activity
    
    try:
        # Forked agent path - tries to reuse main conversation's prompt cache
        if PROMPT_CACHE_SHARING_ENABLED:
            try:
                result = await run_forked_agent({
                    "prompt_messages": [summary_request],
                    "cache_safe_params": cache_safe_params,
                    "can_use_tool": create_compact_can_use_tool(),
                    "query_source": "compact",
                    "fork_label": "compact",
                    "max_turns": 1,
                    "skip_cache_write": True,
                    "overrides": {
                        "abort_controller": getattr(context, 'abort_controller', None),
                    },
                })
                
                assistant_msg = get_last_assistant_message(result.get("messages", []))
                if assistant_msg:
                    assistant_text = extract_text_from_response(assistant_msg)
                    if assistant_text and not assistant_msg.get("is_api_error_message", False):
                        if not assistant_text.startswith(ERROR_MESSAGE_PROMPT_TOO_LONG):
                            log_event("tengu_compact_cache_sharing_success", {
                                "pre_compact_token_count": pre_compact_token_count,
                                "output_tokens": result.get("total_usage", {}).get("output_tokens", 0),
                            })
                        return assistant_msg
                
                log_for_debugging(
                    f"Compact cache sharing: no text in response, falling back. Response: {assistant_msg}",
                    level="warn",
                )
                log_event("tengu_compact_cache_sharing_fallback", {
                    "reason": "no_text_response",
                    "pre_compact_token_count": pre_compact_token_count,
                })
            except Exception as e:
                log_error(e)
                log_event("tengu_compact_cache_sharing_fallback", {
                    "reason": "error",
                    "pre_compact_token_count": pre_compact_token_count,
                })
        
        # Regular streaming path (fallback when cache sharing fails or is disabled)
        return await stream_compact_summary_fallback(
            messages=messages,
            summary_request=summary_request,
            context=context,
            pre_compact_token_count=pre_compact_token_count,
        )
    
    finally:
        if activity_interval:
            clear_interval(activity_interval)


async def stream_compact_summary_fallback(
    messages: list,
    summary_request: dict,
    context,
    pre_compact_token_count: int,
) -> dict:
    """Fallback streaming path for compact summary generation."""
    max_attempts = MAX_COMPACT_STREAMING_RETRIES if STREAMING_RETRY_ENABLED else 1
    
    for attempt in range(1, max_attempts + 1):
        has_started_streaming = False
        response = None
        
        # Strip images and reinjected attachments from messages
        stripped_messages = strip_images_from_messages(
            strip_reinjected_attachments(messages)
        )
        
        # Get messages after compact boundary if any
        messages_after_boundary = get_messages_after_compact_boundary(stripped_messages)
        
        # Normalize messages for API
        normalized = normalize_messages_for_api(
            [*messages_after_boundary, summary_request],
            context.options.tools if context.options else [],
        )
        
        # Create streaming generator
        streaming_gen = query_model_with_streaming({
            "messages": normalized,
            "system_prompt": ["You are a helpful AI assistant tasked with summarizing conversations."],
            "thinking_config": {"type": "disabled"},
            "tools": [get_file_read_tool()],  # Only FileReadTool for compaction
            "signal": getattr(context, 'abort_controller', None),
            "options": {
                "get_tool_permission_context": lambda: context.get_app_state().tool_permission_context,
                "model": context.options.main_loop_model if context.options else "claude-sonnet-4-20250514",
                "is_non_interactive_session": context.options.is_non_interactive_session if context.options else False,
                "has_append_system_prompt": bool(context.options.append_system_prompt if context.options else False),
                "max_output_tokens_override": min(
                    20000,  # COMPACT_MAX_OUTPUT_TOKENS
                    8000,  # Max output tokens
                ),
                "query_source": "compact",
                "agents": context.options.agent_definitions.active_agents if context.options else [],
                "mcp_tools": [],
                "effort_value": context.get_app_state().effort_value if context.get_app_state else None,
            },
        })
        
        stream_iter = streaming_gen[Symbol.async_iterator]()
        next_result = await stream_iter.next()
        
        while not next_result.done:
            event = next_result.value
            
            if (
                not has_started_streaming
                and event.get("type") == "stream_event"
                and event.get("event", {}).get("type") == "content_block_start"
                and event.get("event", {}).get("content_block", {}).get("type") == "text"
            ):
                has_started_streaming = True
            
            if (
                event.get("type") == "stream_event"
                and event.get("event", {}).get("type") == "content_block_delta"
                and event.get("event", {}).get("delta", {}).get("type") == "text_delta"
            ):
                pass  # Would update response length
            
            if event.get("type") == "assistant":
                response = event
            
            next_result = await stream_iter.next()
        
        if response:
            return response
        
        if attempt < max_attempts:
            log_event("tengu_compact_streaming_retry", {
                "attempt": attempt,
                "pre_compact_token_count": pre_compact_token_count,
                "has_started_streaming": has_started_streaming,
            })
            await sleep(1.0, getattr(context, 'abort_controller', None))
            continue
        
        log_for_debugging(
            f"Compact streaming failed after {attempt} attempts. hasStartedStreaming={has_started_streaming}",
            level="error",
        )
        log_event("tengu_compact_failed", {
            "reason": "no_streaming_response",
            "pre_compact_token_count": pre_compact_token_count,
            "has_started_streaming": has_started_streaming,
            "retry_enabled": STREAMING_RETRY_ENABLED,
            "attempts": attempt,
            "prompt_cache_sharing_enabled": PROMPT_CACHE_SHARING_ENABLED,
        })
        raise ValueError(ERROR_MESSAGE_INCOMPLETE_RESPONSE)
    
    raise ValueError(ERROR_MESSAGE_INCOMPLETE_RESPONSE)


# Utility functions that need proper implementations

def cache_to_object(read_file_state) -> dict:
    """Convert file state cache to object/dict."""
    if read_file_state is None:
        return {}
    if hasattr(read_file_state, 'cache'):
        return dict(read_file_state.cache) if hasattr(read_file_state, 'cache') else {}
    if isinstance(read_file_state, dict):
        return read_file_state
    return {}


def extract_text_from_response(response) -> str | None:
    """Extract text content from assistant response."""
    if not response:
        return None
    
    content = None
    
    if hasattr(response, 'message') and hasattr(response.message, 'content'):
        content = response.message.content
    elif isinstance(response, dict):
        content = response.get("message", {}).get("content")
    elif isinstance(response, list):
        for block in response:
            if block.get("type") == "text":
                content = block.get("text")
                break
    
    if content is None:
        return None
    
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        for block in content:
            if block.get("type") == "text":
                return block.get("text")
    
    return None


def get_last_assistant_message(messages: list) -> dict | None:
    """Get the last assistant message from a list."""
    for msg in reversed(messages):
        if msg.get("type") == "assistant":
            return msg
    return None


async def run_forked_agent(params: dict) -> dict:
    """Run a forked agent for cache-efficient summarization.
    
    This is a placeholder - actual implementation would spawn a short-lived
    agent with the summarization prompt.
    """
    # Placeholder implementation
    return {
        "messages": [],
        "total_usage": {
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "input_tokens": 0,
        },
    }


async def query_model_with_streaming(params: dict):
    """Query model with streaming response.
    
    Placeholder - actual implementation would call the API with streaming.
    """
    # Placeholder - returns async generator
    async def generator():
        yield {
            "type": "assistant",
            "message": {
                "content": [{
                    "type": "text",
                    "text": "Summary placeholder",
                }],
            },
        }
    return generator()


async def sleep(duration: float, signal=None, abort_error: Callable = None) -> None:
    """Sleep with optional abort support."""
    import asyncio
    try:
        await asyncio.sleep(duration)
    except asyncio.CancelledError:
        if abort_error:
            raise abort_error()
        raise


def clear_interval(interval) -> None:
    """Clear an interval timer."""
    pass


def get_messages_after_compact_boundary(messages: list) -> list:
    """Get messages after the most recent compact boundary."""
    boundary_idx = -1
    for i, msg in enumerate(messages):
        if msg.get("type") == "system" and msg.get("is_compact_boundary", False):
            boundary_idx = i
    return messages[boundary_idx + 1:] if boundary_idx >= 0 else messages


def normalize_messages_for_api(messages: list, tools: list) -> list:
    """Normalize messages for API format."""
    return messages


def get_file_read_tool() -> dict:
    """Get FileReadTool definition."""
    return {
        "name": "Read",
        "description": "Read file contents",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
            },
        },
    }


async def create_post_compact_file_attachments(
    read_file_state: dict,
    context,
    max_files: int,
    preserved_messages: list = None,
) -> list:
    """Create attachment messages for recently accessed files to restore after compaction.
    
    Re-reads files using FileReadTool to get fresh content with proper validation.
    Files are selected based on recency, but constrained by both file count and token
    budget limits.
    
    Files already present as Read tool results in preservedMessages are skipped.
    """
    preserved_messages = preserved_messages or []
    preserved_read_paths = collect_read_tool_file_paths(preserved_messages)
    
    recent_files = []
    if read_file_state:
        for filename, state in read_file_state.items():
            if should_exclude_from_post_compact_restore(filename, context.agent_id):
                continue
            if expand_path(filename) in preserved_read_paths:
                continue
            recent_files.append({
                "filename": filename,
                "timestamp": state.get("timestamp", 0),
                "content": state.get("content", ""),
            })
    
    # Sort by recency
    recent_files.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_files = recent_files[:max_files]
    
    results = []
    used_tokens = 0
    
    for file in recent_files:
        if used_tokens >= POST_COMPACT_TOKEN_BUDGET:
            break
        
        attachment = await generate_file_attachment(
            file["filename"],
            file.get("content"),
            context,
        )
        
        if attachment:
            attachment_tokens = rough_token_count_estimation(str(attachment))
            if used_tokens + attachment_tokens <= POST_COMPACT_TOKEN_BUDGET:
                used_tokens += attachment_tokens
                results.append(create_attachment_message(attachment))
    
    return results


async def generate_file_attachment(
    filename: str,
    content: str,
    context,
) -> dict | None:
    """Generate file attachment for post-compact restoration."""
    # Placeholder - would read file and truncate to token limit
    if not content:
        return None
    
    truncated = truncate_to_tokens(content, POST_COMPACT_MAX_TOKENS_PER_FILE)
    
    return {
        "type": "file_content",
        "file_path": filename,
        "content": truncated,
        "truncated": len(content) > len(truncated),
    }


def create_attachment_message(attachment: dict) -> dict:
    """Create an attachment message from an attachment definition."""
    return {
        "type": "attachment",
        "attachment": attachment,
        "uuid": generate_uuid(),
        "timestamp": 0,
    }


def create_plan_attachment_if_needed(agent_id: str = None) -> dict | None:
    """Create a plan file attachment if a plan file exists for the current session."""
    plan_content = get_plan(agent_id)
    
    if not plan_content:
        return None
    
    plan_file_path = get_plan_file_path(agent_id)
    
    return create_attachment_message({
        "type": "plan_file_reference",
        "plan_file_path": plan_file_path,
        "plan_content": plan_content,
    })


def create_skill_attachment_if_needed(agent_id: str = None) -> dict | None:
    """Create attachment for invoked skills to preserve their content across compaction."""
    invoked_skills = get_invoked_skills_for_agent(agent_id)
    
    if not invoked_skills:
        return None
    
    # Sort most-recent-first so budget pressure drops the least-relevant skills
    used_tokens = 0
    skills = []
    
    for skill_name, skill in sorted(
        invoked_skills.items(),
        key=lambda x: x[1].get("invoked_at", 0),
        reverse=True,
    ):
        content = truncate_to_tokens(
            skill.get("content", ""),
            POST_COMPACT_MAX_TOKENS_PER_SKILL,
        )
        tokens = rough_token_count_estimation(content)
        
        if used_tokens + tokens > POST_COMPACT_SKILLS_TOKEN_BUDGET:
            continue
        
        used_tokens += tokens
        skills.append({
            "name": skill_name,
            "path": skill.get("skill_path", ""),
            "content": content,
        })
    
    if not skills:
        return None
    
    return create_attachment_message({
        "type": "invoked_skills",
        "skills": skills,
    })


async def create_plan_mode_attachment_if_needed(context) -> dict | None:
    """Create plan_mode attachment if user is currently in plan mode."""
    app_state = context.get_app_state()
    if not app_state or app_state.tool_permission_context.mode != "plan":
        return None
    
    plan_file_path = get_plan_file_path(context.agent_id)
    plan_exists = get_plan(context.agent_id) is not None
    
    return create_attachment_message({
        "type": "plan_mode",
        "reminder_type": "full",
        "is_sub_agent": bool(context.agent_id),
        "plan_file_path": plan_file_path,
        "plan_exists": plan_exists,
    })


async def create_async_agent_attachments_if_needed(context) -> list:
    """Create attachments for async agents."""
    app_state = context.get_app_state()
    if not app_state or not hasattr(app_state, 'tasks'):
        return []
    
    attachments = []
    
    for task_id, task in app_state.tasks.items():
        if task.get("retrieved", False):
            continue
        if task.get("status") == "pending":
            continue
        if task.get("agent_id") == context.agent_id:
            continue
        
        attachments.append(create_attachment_message({
            "type": "task_status",
            "task_id": task.get("agent_id"),
            "task_type": "local_agent",
            "description": task.get("description"),
            "status": task.get("status"),
            "delta_summary": task.get("progress", {}).get("summary") if task.get("status") == "running" else task.get("error"),
            "output_file_path": task.get("output_file_path"),
        }))
    
    return attachments


def collect_read_tool_file_paths(messages: list) -> set:
    """Scan messages for Read tool_use blocks and collect their file_path inputs."""
    stub_ids = set()
    paths = set()
    
    # Collect stub IDs first
    for message in messages:
        if message.get("type") != "user":
            continue
        content = message.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_result" and isinstance(block.get("content"), str):
                if block["content"].startswith("[file unchanged]"):
                    stub_ids.add(block.get("tool_use_id"))
    
    # Collect file paths from tool_use blocks
    for message in messages:
        if message.get("type") != "assistant":
            continue
        content = message.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") != "tool_use":
                continue
            if block.get("name") != "Read":
                continue
            if block.get("id") in stub_ids:
                continue
            
            input_data = block.get("input", {})
            if isinstance(input_data, dict) and "file_path" in input_data:
                paths.add(expand_path(input_data["file_path"]))
    
    return paths


def truncate_to_tokens(content: str, max_tokens: int) -> str:
    """Truncate content to roughly maxTokens, keeping the head."""
    if rough_token_count_estimation(content) <= max_tokens:
        return content
    
    char_budget = max_tokens * 4 - len(SKILL_TRUNCATION_MARKER)
    return content[:char_budget] + SKILL_TRUNCATION_MARKER


def should_exclude_from_post_compact_restore(filename: str, agent_id: str = None) -> bool:
    """Check if file should be excluded from post-compact restoration."""
    normalized_filename = expand_path(filename)
    
    # Exclude plan files
    try:
        plan_file_path = expand_path(get_plan_file_path(agent_id))
        if normalized_filename == plan_file_path:
            return True
    except:
        pass
    
    # Exclude memory files
    try:
        from .memory_types import MEMORY_TYPE_VALUES
        from .config import get_memory_path
        memory_paths = set()
        for memory_type in MEMORY_TYPE_VALUES:
            memory_paths.add(expand_path(get_memory_path(memory_type)))
        if normalized_filename in memory_paths:
            return True
    except:
        pass
    
    return False


def rough_token_count_estimation(content: str) -> int:
    """Rough estimation of token count for content."""
    if not content:
        return 0
    return len(content) // 4


def expand_path(path: str) -> str:
    """Normalize and expand a file path."""
    if not path:
        return path
    import os
    return os.path.normpath(os.path.expanduser(path))


def get_transcript_path() -> str | None:
    """Get the transcript path for the current session."""
    # Placeholder - would get from session storage
    return None


def re_append_session_metadata() -> None:
    """Re-append session metadata after compaction."""
    pass


def write_session_transcript_segment(messages: list) -> None:
    """Write a reduced transcript segment for pre-compaction messages."""
    pass


def get_plan(agent_id: str = None) -> str | None:
    """Get plan content."""
    return None


def get_plan_file_path(agent_id: str = None) -> str | None:
    """Get plan file path."""
    return None


def get_invoked_skills_for_agent(agent_id: str = None) -> dict:
    """Get invoked skills for agent."""
    return {}


def extract_discovered_tool_names(messages: list) -> set:
    """Extract tool names that were discovered/used from messages."""
    tool_names = set()
    for message in messages:
        if message.get("type") != "assistant":
            continue
        content = message.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                tool_names.add(block.get("name"))
    return tool_names


def get_deferred_tools_delta_attachment(tools: list, model: str, preserved_messages: list) -> list:
    """Get deferred tools delta attachment for compaction."""
    return []


def get_agent_listing_delta_attachment(context, preserved_messages: list) -> list:
    """Get agent listing delta attachment for compaction."""
    return []


def get_mcp_instructions_delta_attachment(mcp_clients: list, tools: list, model: str, preserved_messages: list) -> list:
    """Get MCP instructions delta attachment for compaction."""
    return []


def extract_compaction_usage(response) -> CompactionUsage | None:
    """Extract token usage from compaction API response."""
    if not response:
        return None
    
    usage = getattr(response, 'usage', None)
    if not usage:
        return None
    
    return CompactionUsage(
        input_tokens=getattr(usage, 'input_tokens', 0),
        output_tokens=getattr(usage, 'output_tokens', 0),
        cache_read_input_tokens=getattr(usage, 'cache_read_input_tokens', 0),
        cache_creation_input_tokens=getattr(usage, 'cache_creation_input_tokens', 0),
    )


def notify_compaction(query_source: str, agent_id: str) -> None:
    """Notify prompt cache break detection of compaction."""
    pass


# Alias for backwards compatibility
CompactService = None


def get_compact_strategy(
    messages: list,
    token_count: int,
    model: str,
) -> CompactStrategy:
    """Determine compaction strategy based on token count and message properties."""
    threshold = get_auto_compact_threshold(model)
    
    if token_count >= threshold:
        return CompactStrategy.FULL
    
    if len(messages) > 20:
        return CompactStrategy.MICRO
    
    return CompactStrategy.FULL


def _calculate_message_priority(message: dict, index: int, total: int) -> float:
    """Calculate priority score for a message (higher = more important to keep).
    
    Lower priority messages are compacted first.
    """
    msg_type = message.get("type", "")
    
    # System messages and compact boundaries have highest priority
    if msg_type == "system":
        if message.get("is_compact_boundary"):
            return 1000.0
        return 900.0
    
    # Recent messages have higher priority
    recency_factor = (index / total) if total > 0 else 0
    base_priority = 500.0 + (recency_factor * 500.0)
    
    if msg_type == "user":
        content = message.get("message", {}).get("content", "")
        # User messages with instructions or questions are important
        if isinstance(content, str):
            if any(kw in content.lower() for kw in ["please", "can you", "could you", "how", "what", "why", "help"]):
                base_priority += 100.0
        elif isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "").lower()
                    if any(kw in text for kw in ["please", "can you", "could you", "how", "what", "why", "help"]):
                        base_priority += 100.0
                        break
    elif msg_type == "assistant":
        base_priority += 50.0  # Assistant messages are generally important
        content = message.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    base_priority += 30.0  # Tool use indicates active work
    
    # Tool results have lower priority (can be summarized away)
    if msg_type == "user":
        content = message.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    base_priority -= 50.0
                    break
    
    return max(0.0, base_priority)


def _compact_messages_iteration(
    messages: list,
    target_tokens: int,
    keep_recent: int,
) -> tuple[list, int]:
    """Single iteration of message compaction.
    
    Returns (compacted_messages, tokens_removed).
    """
    if not messages:
        return [], 0
    
    total_tokens = sum(estimate_message_tokens([m]) for m in messages)
    
    if total_tokens <= target_tokens:
        return messages, 0
    
    # Calculate priorities for all messages
    prioritized = []
    for i, msg in enumerate(messages):
        priority = _calculate_message_priority(msg, i, len(messages))
        tokens = estimate_message_tokens([msg])
        prioritized.append((i, msg, priority, tokens))
    
    # Sort by priority (lowest first = compact these first)
    prioritized.sort(key=lambda x: x[2])
    
    # Always keep the most recent messages
    keep_count = min(keep_recent, len(messages))
    protected_indices = set()
    for i, _, _, _ in prioritized[-keep_count:]:
        protected_indices.add(i)
    
    # Build result keeping protected and high-priority messages
    result = []
    removed_tokens = 0
    
    for i, msg, priority, tokens in prioritized:
        if i in protected_indices:
            result.append((i, msg))
            continue
        
        # Check if we can afford to keep this message
        current_total = sum(estimate_message_tokens([m]) for _, m in result) + tokens
        if current_total <= target_tokens:
            result.append((i, msg))
        else:
            removed_tokens += tokens
    
    # Reconstruct message list maintaining order
    result.sort(key=lambda x: x[0])
    return [msg for _, msg in result], removed_tokens


def compact_messages(
    messages: list,
    max_tokens: int = 100000,
    keep_recent: int = 10,
) -> CompactionResult:
    """Compact messages to fit within token budget using priority-based removal.
    
    Args:
        messages: List of conversation messages
        max_tokens: Target maximum token count after compaction
        keep_recent: Number of most recent messages to always preserve
    
    Returns:
        CompactionResult with boundary marker and summary messages
    """
    if not messages:
        return CompactionResult(
            boundary_marker=None,
            summary_messages=[],
            attachments=[],
            hook_results=[],
        )
    
    total_tokens = sum(estimate_message_tokens([m]) for m in messages)
    
    if total_tokens <= max_tokens:
        return CompactionResult(
            boundary_marker=None,
            summary_messages=[],
            attachments=[],
            hook_results=[],
        )
    
    # Iteratively compact until within budget
    current_messages = list(messages)
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        compacted, removed = _compact_messages_iteration(
            current_messages,
            max_tokens,
            keep_recent,
        )
        
        if not compacted:
            break
        
        current_tokens = sum(estimate_message_tokens([m]) for m in compacted)
        if current_tokens <= max_tokens:
            current_messages = compacted
            break
        
        current_messages = compacted
        iteration += 1
    
    # If still over budget, we need to do aggressive compaction
    # Keep only system messages and the most recent keep_recent messages
    if sum(estimate_message_tokens([m]) for m in current_messages) > max_tokens:
        protected = []
        for msg in current_messages:
            msg_type = msg.get("type", "")
            if msg_type == "system":
                protected.append(msg)
        
        recent_count = 0
        for msg in reversed(current_messages):
            if recent_count >= keep_recent:
                break
            if msg.get("type") in ("user", "assistant"):
                protected.append(msg)
                recent_count += 1
        
        current_messages = protected
    
    final_tokens = sum(estimate_message_tokens([m]) for m in current_messages)
    
    boundary_marker = None
    if current_messages != messages:
        boundary_marker = {
            "type": "system",
            "is_compact_boundary": True,
            "uuid": generate_uuid(),
            "timestamp": 0,
            "compact_metadata": {
                "mode": "reactive",
                "pre_compact_token_count": total_tokens,
                "post_compact_token_count": final_tokens,
            },
        }
    
    return CompactionResult(
        boundary_marker=boundary_marker,
        summary_messages=[],
        attachments=[],
        hook_results=[],
        messages_to_keep=current_messages if current_messages != messages else None,
        pre_compact_token_count=total_tokens,
        post_compact_token_count=final_tokens,
    )


class CompactService:
    """Main compaction service class."""
    
    def __init__(self, config: CompactConfig = None):
        self.config = config or CompactConfig()
    
    async def compact(
        self,
        messages: list,
        context,
        cache_safe_params: dict,
        **kwargs,
    ) -> CompactionResult:
        """Perform full compaction."""
        return await compact_conversation(messages, context, cache_safe_params, **kwargs)
    
    async def partial_compact(
        self,
        messages: list,
        pivot_index: int,
        context,
        cache_safe_params: dict,
        **kwargs,
    ) -> CompactionResult:
        """Perform partial compaction around pivot index."""
        return await partial_compact_conversation(
            messages, pivot_index, context, cache_safe_params, **kwargs
        )
    
    def get_strategy(
        self,
        messages: list,
        token_count: int,
        model: str,
    ) -> CompactStrategy:
        """Determine compaction strategy."""
        return get_compact_strategy(messages, token_count, model)
    
    async def auto_compact(
        self,
        messages: list,
        context,
        cache_safe_params: dict,
        query_source: str = None,
    ) -> CompactionResult | None:
        """Perform automatic compaction if needed."""
        from .auto_compact import auto_compact_if_needed
        
        result = await auto_compact_if_needed(
            messages=messages,
            tool_use_context=context,
            cache_safe_params=cache_safe_params,
            query_source=query_source,
        )
        
        if result.get("was_compacted"):
            return result.get("compaction_result")
        return None


__all__ = [
    "CompactionBudget",
    "CompactionResult",
    "CompactionUsage",
    "CompactConfig",
    "CompactMetadata",
    "CompactService",
    "CompactStrategy",
    "ERROR_MESSAGE_INCOMPLETE_RESPONSE",
    "ERROR_MESSAGE_NOT_ENOUGH_MESSAGES",
    "ERROR_MESSAGE_PROMPT_TOO_LONG",
    "ERROR_MESSAGE_USER_ABORT",
    "MARKER_COMPACT_BOUNDARY",
    "MARKER_SUMMARY_END",
    "MARKER_SUMMARY_START",
    "PartialCompactDirection",
    "PostCompactCleanupResult",
    "PRESERVE_REASONS",
    "PreservedSegment",
    "RecompactionInfo",
    "SummarizeMetadata",
    "annotate_boundary_with_preserved_segment",
    "build_post_compact_messages",
    "compact_conversation",
    "compact_conversation",
    "compact_messages",
    "create_compact_boundary_message",
    "create_compact_can_use_tool",
    "format_compact_summary",
    "get_compact_prompt",
    "get_compact_strategy",
    "get_compact_user_summary_message",
    "get_partial_compact_prompt",
    "merge_hook_instructions",
    "partial_compact_conversation",
    "POST_COMPACT_MAX_FILES_TO_RESTORE",
    "POST_COMPACT_MAX_TOKENS_PER_FILE",
    "POST_COMPACT_MAX_TOKENS_PER_SKILL",
    "POST_COMPACT_SKILLS_TOKEN_BUDGET",
    "POST_COMPACT_TOKEN_BUDGET",
    "run_post_compact_cleanup",
    "should_preserve_message",
    "strip_images_from_messages",
    "strip_reinjected_attachments",
    "suppress_compact_warning",
]
