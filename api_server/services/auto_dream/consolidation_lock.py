"""
File-based lock management for memory consolidation.

Uses mtime semantics: lock file's mtime = lastConsolidatedAt.
This allows atomic lock acquisition with timestamp semantics.
"""
import asyncio
import os
import time
from pathlib import Path
from typing import List, Optional

from .constants import LOCK_FILE_NAME


def _get_memory_dir() -> Path:
    return Path.home() / ".claude" / "memory"


def _get_lock_file_path() -> Path:
    return _get_memory_dir() / LOCK_FILE_NAME


def _get_sessions_dir() -> Path:
    return Path.home() / ".claude" / "sessions"


def read_last_consolidated_at() -> float:
    """
    Read the last consolidated timestamp from lock file mtime.
    
    Returns:
        Unix timestamp in milliseconds, or 0 if lock file doesn't exist.
    """
    lock_path = _get_lock_file_path()
    if not lock_path.exists():
        return 0.0
    try:
        stat = lock_path.stat()
        return stat.st_mtime * 1000
    except OSError:
        return 0.0


def try_acquire_consolidation_lock() -> Optional[float]:
    """
    Try to acquire the consolidation lock.
    
    Uses non-blocking check: if lock file exists with recent mtime,
    another process is mid-consolidation.
    
    Returns:
        Prior mtime (lastConsolidatedAt) if lock is held by another process,
        None if lock was acquired.
    """
    lock_path = _get_lock_file_path()
    memory_dir = _get_memory_dir()
    
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    if lock_path.exists():
        try:
            stat = lock_path.stat()
            mtime_ms = stat.st_mtime * 1000
            return mtime_ms
        except OSError:
            pass
    
    try:
        lock_path.touch()
        return None
    except OSError:
        return None


def rollback_consolidation_lock(prior_mtime: float) -> None:
    """
    Rollback lock file to prior mtime after failed consolidation.
    
    Args:
        prior_mtime: Previous lastConsolidatedAt timestamp in ms.
    """
    lock_path = _get_lock_file_path()
    if prior_mtime <= 0:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    
    try:
        lock_path.touch()
        os.utime(lock_path, (prior_mtime / 1000, prior_mtime / 1000))
    except OSError:
        pass


def record_consolidation() -> float:
    """
    Record successful consolidation by updating lock file mtime.
    
    Returns:
        New consolidation timestamp in milliseconds.
    """
    lock_path = _get_lock_file_path()
    memory_dir = _get_memory_dir()
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    now_ms = time.time() * 1000
    lock_path.touch()
    try:
        os.utime(lock_path, (now_ms / 1000, now_ms / 1000))
    except OSError:
        pass
    return now_ms


def list_sessions_touched_since(since_ms: float) -> List[str]:
    """
    List session IDs that have been modified since the given timestamp.
    
    Args:
        since_ms: Timestamp in milliseconds to check from.
    
    Returns:
        List of session ID strings that have mtime > since_ms.
    """
    sessions_dir = _get_sessions_dir()
    if not sessions_dir.exists():
        return []
    
    since_sec = since_ms / 1000
    touched: List[str] = []
    
    try:
        for entry in sessions_dir.iterdir():
            if not entry.name.endswith(".json"):
                continue
            try:
                stat = entry.stat()
                if stat.st_mtime > since_sec:
                    session_id = entry.stem
                    touched.append(session_id)
            except OSError:
                continue
    except OSError:
        pass
    
    return touched


async def read_last_consolidated_at_async() -> float:
    """Async wrapper for read_last_consolidated_at."""
    return await asyncio.to_thread(read_last_consolidated_at)


async def try_acquire_consolidation_lock_async() -> Optional[float]:
    """Async wrapper for try_acquire_consolidation_lock."""
    return await asyncio.to_thread(try_acquire_consolidation_lock)


async def rollback_consolidation_lock_async(prior_mtime: float) -> None:
    """Async wrapper for rollback_consolidation_lock."""
    await asyncio.to_thread(rollback_consolidation_lock, prior_mtime)


async def record_consolidation_async() -> float:
    """Async wrapper for record_consolidation."""
    return await asyncio.to_thread(record_consolidation)


async def list_sessions_touched_since_async(since_ms: float) -> List[str]:
    """Async wrapper for list_sessions_touched_since."""
    return await asyncio.to_thread(list_sessions_touched_since, since_ms)
