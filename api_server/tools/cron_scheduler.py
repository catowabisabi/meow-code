"""Cron scheduler with lock mechanism - bridging gap with TypeScript cronScheduler.ts"""
import asyncio
import logging
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import os


logger = logging.getLogger(__name__)


class LockAcquisitionError(Exception):
    pass


class CronLock:
    def __init__(self, lock_id: str, ttl_seconds: int = 300):
        self.lock_id = lock_id
        self.ttl_seconds = ttl_seconds
        self.acquired_at: Optional[datetime] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
    
    def release(self) -> None:
        self.acquired_at = None


class FileLock(CronLock):
    def __init__(self, lock_id: str, lock_dir: str = "/tmp/claude_locks", ttl_seconds: int = 300):
        super().__init__(lock_id, ttl_seconds)
        self.lock_dir = lock_dir
        self.lock_file = os.path.join(lock_dir, f"{lock_id}.lock")
    
    def acquire(self) -> bool:
        os.makedirs(self.lock_dir, exist_ok=True)
        
        if os.path.exists(self.lock_file):
            try:
                with open(self.lock_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        acquired_at = datetime.fromisoformat(content)
                        age = (datetime.now() - acquired_at).total_seconds()
                        if age < self.ttl_seconds:
                            return False
            except (ValueError, OSError):
                pass
        
        try:
            with open(self.lock_file, 'w') as f:
                f.write(datetime.now().isoformat())
            self.acquired_at = datetime.now()
            return True
        except OSError:
            return False
    
    def release(self) -> None:
        try:
            if os.path.exists(self.lock_file):
                os.unlink(self.lock_file)
        except OSError:
            pass
        self.acquired_at = None


class DistributedLock(CronLock):
    _locks: Dict[str, 'DistributedLock'] = {}
    
    def __init__(self, lock_id: str, ttl_seconds: int = 300):
        super().__init__(lock_id, ttl_seconds)
    
    def acquire(self) -> bool:
        if self.lock_id in DistributedLock._locks:
            existing = DistributedLock._locks[self.lock_id]
            if existing.acquired_at:
                age = (datetime.now() - existing.acquired_at).total_seconds()
                if age < self.ttl_seconds:
                    return False
        
        self.acquired_at = datetime.now()
        DistributedLock._locks[self.lock_id] = self
        return True
    
    def release(self) -> None:
        if self.lock_id in DistributedLock._locks:
            del DistributedLock._locks[self.lock_id]
        self.acquired_at = None


@dataclass
class CronTask:
    id: str
    name: str
    callback: Callable
    interval_seconds: int
    enabled: bool = True
    run_on_start: bool = False


class CronScheduler:
    def __init__(self, lock_dir: str = "/tmp/claude_locks"):
        self.tasks: Dict[str, CronTask] = {}
        self.running: Dict[str, bool] = {}
        self.lock_dir = lock_dir
        self._task_handle: Optional[asyncio.Task] = None
    
    def add_task(
        self,
        task_id: str,
        name: str,
        callback: Callable,
        interval_seconds: int,
        run_on_start: bool = False
    ) -> None:
        self.tasks[task_id] = CronTask(
            id=task_id,
            name=name,
            callback=callback,
            interval_seconds=interval_seconds,
            run_on_start=run_on_start
        )
    
    def remove_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            del self.tasks[task_id]
    
    def enable_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
    
    def disable_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
    
    async def _run_task(self, task: CronTask, lock: FileLock) -> None:
        task_id = task.id
        
        if task_id in self.running and self.running[task_id]:
            logger.warning(f"Task {task_id} already running, skipping")
            return
        
        self.running[task_id] = True
        
        try:
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback()
            else:
                task.callback()
            logger.debug(f"Task {task_id} completed")
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
        finally:
            self.running[task_id] = False
    
    async def _scheduler_loop(self) -> None:
        while True:
            for task_id, task in list(self.tasks.items()):
                if not task.enabled:
                    continue
                
                lock_id = f"cron_{task_id}"
                lock = FileLock(lock_id, self.lock_dir)
                
                if lock.acquire():
                    try:
                        asyncio.create_task(self._run_task(task, lock))
                    finally:
                        lock.release()
            
            await asyncio.sleep(60)
    
    async def start(self) -> None:
        for task_id, task in self.tasks.items():
            if task.run_on_start and task.enabled:
                lock = FileLock(f"cron_{task_id}", self.lock_dir)
                if lock.acquire():
                    try:
                        asyncio.create_task(self._run_task(task, lock))
                    finally:
                        lock.release()
        
        self._task_handle = asyncio.create_task(self._scheduler_loop())
    
    async def stop(self) -> None:
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass


_scheduler: Optional[CronScheduler] = None


def get_cron_scheduler() -> CronScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
    return _scheduler
