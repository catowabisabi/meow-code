"""
Session ingress service for persisting and retrieving session logs.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable

import httpx


MAX_RETRIES = 10
BASE_DELAY_MS = 500


@dataclass
class SessionIngressError:
    error: Optional[Dict[str, str]] = None


last_uuid_map: Dict[str, str] = {}

sequential_append_by_session: Dict[str, Callable] = {}


async def _sleep(ms: float) -> None:
    await asyncio.sleep(ms / 1000)


async def _append_session_log_impl(
    session_id: str,
    entry: Dict[str, Any],
    url: str,
    headers: Dict[str, str],
) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            last_uuid = last_uuid_map.get(session_id)
            request_headers = dict(headers)
            if last_uuid:
                request_headers["Last-Uuid"] = last_uuid

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.put(url, json=entry, headers=request_headers)

            if response.status_code in (200, 201):
                last_uuid_map[session_id] = entry.get("uuid", "")
                return True

            if response.status_code == 409:
                server_last_uuid = response.headers.get("x-last-uuid")
                if server_last_uuid == entry.get("uuid"):
                    last_uuid_map[session_id] = entry.get("uuid", "")
                    return True

                if server_last_uuid:
                    last_uuid_map[session_id] = server_last_uuid
                else:
                    logs = await _fetch_session_logs_from_url(session_id, url, headers)
                    adopted_uuid = _find_last_uuid(logs)
                    if adopted_uuid:
                        last_uuid_map[session_id] = adopted_uuid
                    else:
                        return False
                continue

            if response.status_code == 401:
                return False

        except Exception as error:
            pass

        if attempt == MAX_RETRIES:
            return False

        delay_ms = min(BASE_DELAY_MS * (2 ** (attempt - 1)), 8000)
        await _sleep(delay_ms)

    return False


async def _sequential_wrapper(
    session_id: str,
    func: Callable,
) -> Callable:
    lock = asyncio.Lock()
    
    async def wrapper(*args, **kwargs):
        async with lock:
            return await func(*args, **kwargs)
    return wrapper


async def append_session_log(
    session_id: str,
    entry: Dict[str, Any],
    url: str,
) -> bool:
    session_token = os.environ.get("CLAUDE_SESSION_INGRESS_TOKEN")
    if not session_token:
        return False

    headers: Dict[str, str] = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json",
    }

    if session_id not in sequential_append_by_session:
        sequential_append_by_session[session_id] = await _sequential_wrapper(
            session_id,
            lambda e, u, h: _append_session_log_impl(session_id, e, u, h),
        )

    return await sequential_append_by_session[session_id](entry, url, headers)


async def get_session_logs(
    session_id: str,
    url: str,
) -> Optional[List[Dict[str, Any]]]:
    session_token = os.environ.get("CLAUDE_SESSION_INGRESS_TOKEN")
    if not session_token:
        return None

    headers = {"Authorization": f"Bearer {session_token}"}
    logs = await _fetch_session_logs_from_url(session_id, url, headers)

    if logs and len(logs) > 0:
        last_entry = logs[-1] if logs else None
        if last_entry and "uuid" in last_entry and last_entry.get("uuid"):
            last_uuid_map[session_id] = last_entry["uuid"]

    return logs


async def get_session_logs_via_oauth(
    session_id: str,
    access_token: str,
    org_uuid: str,
) -> Optional[List[Dict[str, Any]]]:
    base_url = os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai")
    url = f"{base_url}/v1/session_ingress/session/{session_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-organization-uuid": org_uuid,
    }
    return await _fetch_session_logs_from_url(session_id, url, headers)


async def get_teleport_events(
    session_id: str,
    access_token: str,
    org_uuid: str,
) -> Optional[List[Dict[str, Any]]]:
    base_url = os.environ.get("CLAUDE_CODE_API_BASE_URL", "https://api.claude.ai")
    url = f"{base_url}/v1/code/sessions/{session_id}/teleport-events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-organization-uuid": org_uuid,
    }

    all_entries: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    pages = 0
    max_pages = 100

    while pages < max_pages:
        params: Dict[str, Any] = {"limit": 1000}
        if cursor:
            params["cursor"] = cursor

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers, params=params)
        except Exception:
            return None

        if response.status_code == 404:
            return None if pages == 0 else all_entries

        if response.status_code == 401:
            raise Exception("Your session has expired. Please run /login to sign in again.")

        if response.status_code != 200:
            return None

        data = response.json()
        events = data.get("data", [])

        if not isinstance(events, list):
            return None

        for ev in events:
            if ev.get("payload") is not None:
                all_entries.append(ev["payload"])

        pages += 1
        next_cursor = data.get("next_cursor")
        if next_cursor is None:
            break
        cursor = next_cursor

    return all_entries


async def _fetch_session_logs_from_url(
    session_id: str,
    url: str,
    headers: Dict[str, str],
) -> Optional[List[Dict[str, Any]]]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            logs = data.get("loglines", [])
            if not isinstance(logs, list):
                return None
            return logs

        if response.status_code == 404:
            return []

        if response.status_code == 401:
            raise Exception("Your session has expired. Please run /login to sign in again.")

        return None
    except Exception:
        return None


def _find_last_uuid(logs: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    if not logs:
        return None
    for entry in reversed(logs):
        if "uuid" in entry and entry.get("uuid"):
            return entry["uuid"]
    return None


def clear_session(session_id: str) -> None:
    last_uuid_map.pop(session_id, None)
    sequential_append_by_session.pop(session_id, None)


def clear_all_sessions() -> None:
    last_uuid_map.clear()
    sequential_append_by_session.clear()
