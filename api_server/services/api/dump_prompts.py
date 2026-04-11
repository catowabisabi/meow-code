import asyncio
import hashlib
import json
import os
from typing import Any, Dict, List, Optional


MAX_CACHED_REQUESTS = 5
cached_api_requests: List[Dict[str, Any]] = []


def _get_session_id() -> str:
    return os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")


def get_dump_prompts_path(agent_id_or_session_id: Optional[str] = None) -> str:
    session_id = agent_id_or_session_id or _get_session_id()
    config_home = os.environ.get("CLAUDE_CONFIG_HOME", os.path.expanduser("~/.claude"))
    return os.path.join(config_home, "dump-prompts", f"{session_id}.jsonl")


async def _append_to_file(file_path: str, entries: List[str]) -> None:
    if not entries:
        return
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n".join(entries) + "\n")
    except Exception:
        pass


def _hash_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


class DumpState:
    def __init__(self):
        self.initialized: bool = False
        self.message_count_seen: int = 0
        self.last_init_data_hash: str = ""
        self.last_init_fingerprint: str = ""


dump_state: Dict[str, DumpState] = {}


def get_last_api_requests() -> List[Dict[str, Any]]:
    return list(cached_api_requests)


def clear_api_request_cache() -> None:
    cached_api_requests.clear()


def clear_dump_state(agent_id_or_session_id: str) -> None:
    dump_state.pop(agent_id_or_session_id, None)


def clear_all_dump_state() -> None:
    dump_state.clear()


def add_api_request_to_cache(request_data: Any) -> None:
    if os.environ.get("USER_TYPE") != "ant":
        return
    cached_api_requests.append({
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "request": request_data,
    })
    if len(cached_api_requests) > MAX_CACHED_REQUESTS:
        cached_api_requests.pop(0)


def _init_fingerprint(req: Dict[str, Any]) -> str:
    tools = req.get("tools", [])
    system = req.get("system", [])

    if isinstance(system, str):
        sys_len = len(system)
    elif isinstance(system, list):
        sys_len = sum(
            (b.get("text", "") or "").__len__() if isinstance(b, dict) else 0
            for b in system
        )
    else:
        sys_len = 0

    tool_names = "|".join(t.get("name", "") if isinstance(t, dict) else "" for t in tools) if tools else ""
    model = req.get("model", "")
    return f"{model}|{tool_names}|{sys_len}"


def _dump_request(
    body: str,
    ts: str,
    state: DumpState,
    file_path: str,
) -> None:
    try:
        req = json.loads(body)
        add_api_request_to_cache(req)

        if os.environ.get("USER_TYPE") != "ant":
            return
        entries: List[str] = []
        messages = req.get("messages", [])

        fingerprint = _init_fingerprint(req)
        if not state.initialized or fingerprint != state.last_init_fingerprint:
            init_data = {k: v for k, v in req.items() if k != "messages"}
            init_data_str = json.dumps(init_data, separators=(",", ":"))
            init_data_hash = _hash_string(init_data_str)
            state.last_init_fingerprint = fingerprint

            if not state.initialized:
                state.initialized = True
                state.last_init_data_hash = init_data_hash
                entries.append(
                    f'{{"type":"init","timestamp":"{ts}","data":{init_data_str}}}'
                )
            elif init_data_hash != state.last_init_data_hash:
                state.last_init_data_hash = init_data_hash
                entries.append(
                    f'{{"type":"system_update","timestamp":"{ts}","data":{init_data_str}}}'
                )

        for msg in messages[state.message_count_seen:]:
            if isinstance(msg, dict) and msg.get("role") == "user":
                entries.append(
                    json.dumps({"type": "message", "timestamp": ts, "data": msg}, separators=(",", ":"))
                )

        state.message_count_seen = len(messages)

        asyncio.create_task(_append_to_file(file_path, entries))
    except Exception:
        pass


def create_dump_prompts_fetch(
    agent_id_or_session_id: str,
):
    file_path = get_dump_prompts_path(agent_id_or_session_id)

    async def fetch_hook(
        input_val: Any,
        init: Optional[Dict[str, Any]] = None,
    ) -> Any:
        nonlocal file_path
        
        state = dump_state.get(agent_id_or_session_id)
        if not state:
            state = DumpState()
            dump_state[agent_id_or_session_id] = state

        timestamp: Optional[str] = None

        if init and init.get("method") == "POST" and init.get("body"):
            timestamp = __import__("datetime").datetime.now().isoformat()
            body = init.get("body")
            if isinstance(body, str):
                asyncio.create_task(asyncio.to_thread(
                    _dump_request, body, timestamp, state, file_path
                ))

        response = await __import__("httpx").AsyncClient().__aenter__()
        result = await response.aclose()

        if timestamp and result is not None and os.environ.get("USER_TYPE") == "ant":
            pass

        return result

    return fetch_hook
