"""Post compaction cleanup - runs after compaction to clear caches and state."""
from .types import PostCompactCleanupResult
from .micro_compact import reset_microcompact_state


def run_post_compact_cleanup(query_source=None) -> PostCompactCleanupResult:
    cleared_caches = []
    cleared_state = []
    
    reset_microcompact_state()
    cleared_state.append("microcompact_state")
    
    is_main_thread = (
        query_source is None
        or query_source.startswith("repl_main_thread")
        or query_source == "sdk"
    )
    
    if is_main_thread:
        cleared_caches.append("user_context_cache")
        cleared_caches.append("memory_files_cache")
    
    cleared_state.append("system_prompt_sections")
    cleared_state.append("classifier_approvals")
    cleared_state.append("speculative_checks")
    cleared_state.append("beta_tracing_state")
    cleared_state.append("session_messages_cache")
    
    return PostCompactCleanupResult(
        cleared_caches=cleared_caches,
        cleared_state=cleared_state,
    )


def cleanup_after_compaction(query_source=None) -> PostCompactCleanupResult:
    return run_post_compact_cleanup(query_source)


def remove_duplicate_context(messages: list) -> list:
    seen = set()
    result = []
    
    for msg in messages:
        key = f"{msg.type}:{getattr(msg, 'uuid', id(msg))}"
        if key not in seen:
            seen.add(key)
            result.append(msg)
    
    return result


def compact_warning_hook(state) -> None:
    pass


class PostCompactCleanup:
    def __init__(self):
        self.cleared_caches = []
        self.cleared_state = []
    
    def cleanup(self, query_source=None) -> PostCompactCleanupResult:
        return run_post_compact_cleanup(query_source)