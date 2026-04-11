"""
Prompt cache break detection for tracking server-side cache breaks.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


MIN_CACHE_MISS_TOKENS = 2000
CACHE_TTL_5MIN_MS = 5 * 60 * 1000
CACHE_TTL_1HOUR_MS = 60 * 60 * 1000
MAX_TRACKED_SOURCES = 10
TRACKED_SOURCE_PREFIXES = [
    "repl_main_thread",
    "sdk",
    "agent:custom",
    "agent:default",
    "agent:builtin",
]


@dataclass
class PendingChanges:
    system_prompt_changed: bool = False
    tool_schemas_changed: bool = False
    model_changed: bool = False
    fast_mode_changed: bool = False
    cache_control_changed: bool = False
    global_cache_strategy_changed: bool = False
    betas_changed: bool = False
    auto_mode_changed: bool = False
    overage_changed: bool = False
    cached_mc_changed: bool = False
    effort_changed: bool = False
    extra_body_changed: bool = False
    added_tool_count: int = 0
    removed_tool_count: int = 0
    system_char_delta: int = 0
    added_tools: List[str] = field(default_factory=list)
    removed_tools: List[str] = field(default_factory=list)
    changed_tool_schemas: List[str] = field(default_factory=list)
    previous_model: str = ""
    new_model: str = ""
    prev_global_cache_strategy: str = ""
    new_global_cache_strategy: str = ""
    added_betas: List[str] = field(default_factory=list)
    removed_betas: List[str] = field(default_factory=list)
    prev_effort_value: str = ""
    new_effort_value: str = ""


@dataclass
class PreviousState:
    system_hash: int = 0
    tools_hash: int = 0
    cache_control_hash: int = 0
    tool_names: List[str] = field(default_factory=list)
    per_tool_hashes: Dict[str, int] = field(default_factory=dict)
    system_char_count: int = 0
    model: str = ""
    fast_mode: bool = False
    global_cache_strategy: str = ""
    betas: List[str] = field(default_factory=list)
    auto_mode_active: bool = False
    is_using_overage: bool = False
    cached_mc_enabled: bool = False
    effort_value: str = ""
    extra_body_hash: int = 0
    call_count: int = 0
    pending_changes: Optional[PendingChanges] = None
    prev_cache_read_tokens: Optional[int] = None
    cache_deletions_pending: bool = False


previous_state_by_source: Dict[str, PreviousState] = {}


def _log_for_debugging(message: str) -> None:
    print(f"[cache-break] {message}", flush=True)


def _log_error(err: Exception) -> None:
    print(f"[cache-break] Error: {err}", flush=True)


def _compute_hash(data: Any) -> int:
    s = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def _is_excluded_model(model: str) -> bool:
    return "haiku" in model.lower()


def _get_tracking_key(query_source: str, agent_id: Optional[str] = None) -> Optional[str]:
    if query_source == "compact":
        return "repl_main_thread"
    for prefix in TRACKED_SOURCE_PREFIXES:
        if query_source.startswith(prefix):
            return agent_id or query_source
    return None


def _strip_cache_control(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {k: v for k, v in item.items() if k != "cache_control"}
        if isinstance(item, dict) else item
        for item in items
    ]


def _sanitize_tool_name(name: str) -> str:
    return "mcp" if name.startswith("mcp__") else name


def _compute_per_tool_hashes(
    stripped_tools: List[Any],
    names: List[str],
) -> Dict[str, int]:
    hashes: Dict[str, int] = {}
    for i, tool in enumerate(stripped_tools):
        key = names[i] if i < len(names) else f"__idx_{i}"
        hashes[key] = _compute_hash(tool)
    return hashes


def _get_system_char_count(system: List[Dict[str, Any]]) -> int:
    total = 0
    for block in system:
        if isinstance(block, dict) and "text" in block:
            total += len(block.get("text", ""))
    return total


def _build_diffable_content(
    system: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: str,
) -> str:
    system_text = "\n\n".join(
        b.get("text", "") if isinstance(b, dict) else ""
        for b in system
    )
    
    tool_details: List[str] = []
    for t in tools:
        if not isinstance(t, dict):
            tool_details.append("unknown")
            continue
        name = t.get("name", "unknown")
        desc = t.get("description", "")
        schema = json.dumps(t.get("input_schema", {}), sort_keys=True)
        tool_details.append(f"{name}\n  description: {desc}\n  input_schema: {schema}")
    
    tool_details.sort()
    
    return (
        f"Model: {model}\n\n"
        "=== System Prompt ===\n\n"
        f"{system_text}\n\n"
        f"=== Tools ({len(tools)}) ===\n\n"
        + "\n\n".join(tool_details)
    )


def record_prompt_state(
    system: List[Dict[str, Any]],
    tool_schemas: List[Dict[str, Any]],
    query_source: str,
    model: str,
    agent_id: Optional[str] = None,
    fast_mode: bool = False,
    global_cache_strategy: str = "",
    betas: Optional[List[str]] = None,
    auto_mode_active: bool = False,
    is_using_overage: bool = False,
    cached_mc_enabled: bool = False,
    effort_value: Optional[str] = None,
    extra_body_params: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        betas = betas or []
        key = _get_tracking_key(query_source, agent_id)
        if not key:
            return

        stripped_system = _strip_cache_control(system)
        stripped_tools = _strip_cache_control(tool_schemas)

        system_hash = _compute_hash(stripped_system)
        tools_hash = _compute_hash(stripped_tools)
        cache_control_hash = _compute_hash([
            b.get("cache_control") if isinstance(b, dict) else None
            for b in system
        ])
        
        tool_names = [
            t.get("name", "unknown") if isinstance(t, dict) else "unknown"
            for t in tool_schemas
        ]
        
        system_char_count = _get_system_char_count(system)
        is_fast_mode = fast_mode
        sorted_betas = sorted(betas)
        effort_str = effort_value if effort_value else ""
        extra_body_hash = _compute_hash(extra_body_params) if extra_body_params else 0

        prev = previous_state_by_source.get(key)

        if not prev:
            while len(previous_state_by_source) >= MAX_TRACKED_SOURCES:
                oldest_key = next(iter(previous_state_by_source))
                previous_state_by_source.pop(oldest_key, None)

            previous_state_by_source[key] = PreviousState(
                system_hash=system_hash,
                tools_hash=tools_hash,
                cache_control_hash=cache_control_hash,
                tool_names=tool_names,
                system_char_count=system_char_count,
                model=model,
                fast_mode=is_fast_mode,
                global_cache_strategy=global_cache_strategy,
                betas=sorted_betas,
                auto_mode_active=auto_mode_active,
                is_using_overage=is_using_overage,
                cached_mc_enabled=cached_mc_enabled,
                effort_value=effort_str,
                extra_body_hash=extra_body_hash,
                call_count=1,
                pending_changes=None,
                prev_cache_read_tokens=None,
                cache_deletions_pending=False,
            )
            return

        prev.call_count += 1

        system_prompt_changed = system_hash != prev.system_hash
        tool_schemas_changed = tools_hash != prev.tools_hash
        model_changed = model != prev.model
        fast_mode_changed = is_fast_mode != prev.fast_mode
        cache_control_changed = cache_control_hash != prev.cache_control_hash
        global_cache_strategy_changed = global_cache_strategy != prev.global_cache_strategy
        
        betas_changed = (
            len(sorted_betas) != len(prev.betas) or
            any(b != prev.betas[i] for i, b in enumerate(sorted_betas) if i < len(prev.betas))
        )
        
        auto_mode_changed = auto_mode_active != prev.auto_mode_active
        overage_changed = is_using_overage != prev.is_using_overage
        cached_mc_changed = cached_mc_enabled != prev.cached_mc_enabled
        effort_changed = effort_str != prev.effort_value
        extra_body_changed = extra_body_hash != prev.extra_body_hash

        if any([
            system_prompt_changed,
            tool_schemas_changed,
            model_changed,
            fast_mode_changed,
            cache_control_changed,
            global_cache_strategy_changed,
            betas_changed,
            auto_mode_changed,
            overage_changed,
            cached_mc_changed,
            effort_changed,
            extra_body_changed,
        ]):
            prev_tool_set = set(prev.tool_names)
            new_tool_set = set(tool_names)
            added_tools = [n for n in tool_names if n not in prev_tool_set]
            removed_tools = [n for n in prev.tool_names if n not in new_tool_set]
            changed_tool_schemas: List[str] = []

            if tool_schemas_changed:
                new_hashes = _compute_per_tool_hashes(stripped_tools, tool_names)
                for name in tool_names:
                    if name in prev_tool_set:
                        if new_hashes.get(name) != prev.per_tool_hashes.get(name):
                            changed_tool_schemas.append(name)
                prev.per_tool_hashes = new_hashes

            prev.pending_changes = PendingChanges(
                system_prompt_changed=system_prompt_changed,
                tool_schemas_changed=tool_schemas_changed,
                model_changed=model_changed,
                fast_mode_changed=fast_mode_changed,
                cache_control_changed=cache_control_changed,
                global_cache_strategy_changed=global_cache_strategy_changed,
                betas_changed=betas_changed,
                auto_mode_changed=auto_mode_changed,
                overage_changed=overage_changed,
                cached_mc_changed=cached_mc_changed,
                effort_changed=effort_changed,
                extra_body_changed=extra_body_changed,
                added_tool_count=len(added_tools),
                removed_tool_count=len(removed_tools),
                added_tools=added_tools,
                removed_tools=removed_tools,
                changed_tool_schemas=changed_tool_schemas,
                system_char_delta=system_char_count - prev.system_char_count,
                previous_model=prev.model,
                new_model=model,
                prev_global_cache_strategy=prev.global_cache_strategy,
                new_global_cache_strategy=global_cache_strategy,
                added_betas=[b for b in sorted_betas if b not in set(prev.betas)],
                removed_betas=[b for b in prev.betas if b not in set(sorted_betas)],
                prev_effort_value=prev.effort_value,
                new_effort_value=effort_str,
            )
        else:
            prev.pending_changes = None

        prev.system_hash = system_hash
        prev.tools_hash = tools_hash
        prev.cache_control_hash = cache_control_hash
        prev.tool_names = tool_names
        prev.system_char_count = system_char_count
        prev.model = model
        prev.fast_mode = is_fast_mode
        prev.global_cache_strategy = global_cache_strategy
        prev.betas = sorted_betas
        prev.auto_mode_active = auto_mode_active
        prev.is_using_overage = is_using_overage
        prev.cached_mc_enabled = cached_mc_enabled
        prev.effort_value = effort_str
        prev.extra_body_hash = extra_body_hash

    except Exception as e:
        _log_error(e)


async def check_response_for_cache_break(
    query_source: str,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    messages: List[Dict[str, Any]],
    agent_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    try:
        key = _get_tracking_key(query_source, agent_id)
        if not key:
            return

        state = previous_state_by_source.get(key)
        if not state:
            return

        if _is_excluded_model(state.model):
            return

        prev_cache_read = state.prev_cache_read_tokens
        state.prev_cache_read_tokens = cache_read_tokens

        if prev_cache_read is None:
            return

        if state.cache_deletions_pending:
            state.cache_deletions_pending = False
            state.pending_changes = None
            return

        token_drop = prev_cache_read - cache_read_tokens
        if cache_read_tokens >= prev_cache_read * 0.95 or token_drop < MIN_CACHE_MISS_TOKENS:
            state.pending_changes = None
            return

        changes = state.pending_changes
        parts: List[str] = []

        if changes:
            if changes.model_changed:
                parts.append(f"model changed ({changes.previous_model} -> {changes.new_model})")
            if changes.system_prompt_changed:
                char_delta = changes.system_char_delta
                char_info = "" if char_delta == 0 else f" (+{char_delta} chars)" if char_delta > 0 else f" ({char_delta} chars)"
                parts.append(f"system prompt changed{char_info}")
            if changes.tool_schemas_changed:
                if changes.added_tool_count > 0 or changes.removed_tool_count > 0:
                    parts.append(f"tools changed (+{changes.added_tool_count}/-{changes.removed_tool_count} tools)")
                else:
                    parts.append("tools changed (tool prompt/schema changed, same tool set)")
            if changes.fast_mode_changed:
                parts.append("fast mode toggled")
            if changes.global_cache_strategy_changed:
                parts.append(f"global cache strategy changed ({changes.prev_global_cache_strategy or 'none'} -> {changes.new_global_cache_strategy or 'none'})")
            if changes.cache_control_changed and not changes.global_cache_strategy_changed and not changes.system_prompt_changed:
                parts.append("cache_control changed (scope or TTL)")
            if changes.betas_changed:
                added = ",".join(changes.added_betas) if changes.added_betas else ""
                removed = ",".join(changes.removed_betas) if changes.removed_betas else ""
                diff_parts = []
                if added:
                    diff_parts.append(f"+{added}")
                if removed:
                    diff_parts.append(f"-{removed}")
                diff_str = " ".join(diff_parts)
                parts.append(f"betas changed ({diff_str})" if diff_str else "betas changed")
            if changes.auto_mode_changed:
                parts.append("auto mode toggled")
            if changes.overage_changed:
                parts.append("overage state changed (TTL latched, no flip)")
            if changes.cached_mc_changed:
                parts.append("cached microcompact toggled")
            if changes.effort_changed:
                parts.append(f"effort changed ({changes.prev_effort_value or 'default'} -> {changes.new_effort_value or 'default'})")
            if changes.extra_body_changed:
                parts.append("extra body params changed")

        last_assistant_msg = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("type") == "assistant":
                last_assistant_msg = msg
                break

        time_since_last_assistant_msg: Optional[float] = None
        if last_assistant_msg and isinstance(last_assistant_msg, dict):
            timestamp = last_assistant_msg.get("timestamp")
            if timestamp:
                try:
                    msg_time = time.mktime(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"))
                    time_since_last_assistant_msg = time.time() - msg_time
                except (ValueError, TypeError):
                    pass

        last_assistant_msg_over_5min = (
            time_since_last_assistant_msg is not None and
            time_since_last_assistant_msg > CACHE_TTL_5MIN_MS / 1000
        )
        last_assistant_msg_over_1h = (
            time_since_last_assistant_msg is not None and
            time_since_last_assistant_msg > CACHE_TTL_1HOUR_MS / 1000
        )

        if parts:
            reason = ", ".join(parts)
        elif last_assistant_msg_over_1h:
            reason = "possible 1h TTL expiry (prompt unchanged)"
        elif last_assistant_msg_over_5min:
            reason = "possible 5min TTL expiry (prompt unchanged)"
        elif time_since_last_assistant_msg is not None:
            reason = "likely server-side (prompt unchanged, <5min gap)"
        else:
            reason = "unknown cause"

        _log_for_debugging(
            f"[PROMPT CACHE BREAK] {reason} [source={query_source}, call #{state.call_count}, "
            f"cache read: {prev_cache_read} -> {cache_read_tokens}, creation: {cache_creation_tokens}]"
        )

        state.pending_changes = None

    except Exception as e:
        _log_error(e)


def notify_cache_deletion(query_source: str, agent_id: Optional[str] = None) -> None:
    key = _get_tracking_key(query_source, agent_id)
    state = previous_state_by_source.get(key) if key else None
    if state:
        state.cache_deletions_pending = True


def notify_compaction(query_source: str, agent_id: Optional[str] = None) -> None:
    key = _get_tracking_key(query_source, agent_id)
    state = previous_state_by_source.get(key) if key else None
    if state:
        state.prev_cache_read_tokens = None


def cleanup_agent_tracking(agent_id: str) -> None:
    previous_state_by_source.pop(agent_id, None)


def reset_prompt_cache_break_detection() -> None:
    previous_state_by_source.clear()
