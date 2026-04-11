"""
Section cache - ported from src/constants/systemPromptSections.ts
"""

import functools
from typing import Callable, Awaitable

SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__"

_cache: dict[str, str] = {}
_uncached: dict[str, str] = {}


def system_prompt_section(name: str, compute_fn: Callable[[], str | None]) -> str | None:
    """
    Memoized system prompt section.
    Cached - use when section content is stable across turns.
    """
    if name in _cache:
        return _cache[name]
    
    result = compute_fn()
    if result is not None:
        _cache[name] = result
    return result


def uncached_system_prompt_section(
    name: str,
    compute_fn: Callable[[], str | None],
    reason: str,
) -> str | None:
    """
    Uncached system prompt section.
    Use when section content varies per-turn (e.g., MCP servers connect/disconnect).
    """
    return compute_fn()


def clear_prompt_cache() -> None:
    """Clear all cached sections"""
    _cache.clear()


def resolve_sections(
    sections: list[tuple[str, Callable[[], str | None], bool]],
) -> list[str | None]:
    """
    Resolve a list of sections, applying caching as needed.
    Each tuple is (name, compute_fn, is_cached).
    """
    results: list[str | None] = []
    for name, compute_fn, is_cached in sections:
        if is_cached:
            results.append(system_prompt_section(name, compute_fn))
        else:
            results.append(uncached_system_prompt_section(
                name,
                compute_fn,
                f"Section {name} varies per-turn",
            ))
    return results
