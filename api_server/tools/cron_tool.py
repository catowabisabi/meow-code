"""Cron scheduling tool for task automation.

Based on TypeScript cronScheduler.ts and cronTasks.ts implementations.
Provides distributed locking and scheduled task execution.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Callable
from dataclasses import dataclass


@dataclass
class CronTask:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool
    created_at: float
    agent_id: str | None = None


def parse_cron_expression(cron: str) -> tuple[int, int, int, int, int] | None:
    parts = cron.strip().split()
    if len(parts) != 5:
        return None
    try:
        minute, hour, dom, month, dow = parts
        return (
            int(minute) if minute != '*' else -1,
            int(hour) if hour != '*' else -1,
            int(dom) if dom != '*' else -1,
            int(month) if month != '*' else -1,
            int(dow) if dow != '*' else -1,
        )
    except ValueError:
        return None


def cron_to_human(cron: str) -> str:
    parts = cron.strip().split()
    if len(parts) != 5:
        return cron
    
    minute, hour, dom, month, dow = parts
    
    if dom == '*' and month == '*' and dow == '*':
        return f"Every {minute} minutes"
    elif dom == '*' and month == '*':
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        dow_name = days[int(dow)] if dow != '*' else 'daily'
        return f"Every day at {hour}:{minute.zfill(2)}"
    elif dom != '*':
        months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_name = months[int(month)] if month != '*' else ''
        return f"Day {dom} at {hour}:{minute.zfill(2)} {month_name}"
    
    return f"Custom: {cron}"


def next_cron_run_ms(cron: str, now_ms: float) -> float | None:
    import datetime
    parsed = parse_cron_expression(cron)
    if not parsed:
        return None
    
    minute, hour, dom, month, dow = parsed
    now = datetime.datetime.fromtimestamp(now_ms / 1000)
    
    for days_ahead in range(366):
        candidate = now + datetime.timedelta(days=days_ahead)
        
        if month != -1 and candidate.month != month:
            continue
        if dom != -1 and candidate.day != dom:
            continue
        if dow != -1 and candidate.weekday() != dow:
            continue
        
        if hour == -1:
            hour = 0
        if minute == -1:
            minute = 0
        
        candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if candidate > now:
            return candidate.timestamp() * 1000
    
    return None


class CronScheduler:
    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path.home() / ".claude" / "scheduled_tasks.json"
        self._tasks: dict[str, CronTask] = {}
        self._enabled = False
        self._running = False
        self._load_tasks()
    
    def _load_tasks(self) -> None:
        if self._storage_path.exists():
            try:
                data = json.loads(self._storage_path.read_text())
                for task_data in data.get("tasks", []):
                    self._tasks[task_data["id"]] = CronTask(**task_data)
            except Exception:
                pass
    
    def _save_tasks(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": [
                {
                    "id": t.id,
                    "cron": t.cron,
                    "prompt": t.prompt,
                    "recurring": t.recurring,
                    "durable": t.durable,
                    "created_at": t.created_at,
                    "agent_id": t.agent_id,
                }
                for t in self._tasks.values()
            ]
        }
        self._storage_path.write_text(json.dumps(data, indent=2))
    
    def add_task(self, cron: str, prompt: str, recurring: bool = True, durable: bool = False, agent_id: str | None = None) -> str:
        import secrets
        task_id = f"cron_{secrets.token_hex(8)}"
        task = CronTask(
            id=task_id,
            cron=cron,
            prompt=prompt,
            recurring=recurring,
            durable=durable,
            created_at=__import__("time").time(),
            agent_id=agent_id,
        )
        self._tasks[task_id] = task
        if durable:
            self._save_tasks()
        return task_id
    
    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            task = self._tasks[task_id]
            del self._tasks[task_id]
            if task.durable:
                self._save_tasks()
            return True
        return False
    
    def list_tasks(self) -> list[CronTask]:
        return list(self._tasks.values())
    
    async def start(self, on_fire: Callable[[CronTask], None]) -> None:
        self._running = True
        while self._running and self._enabled:
            now = __import__("time").time() * 1000
            for task in list(self._tasks.values()):
                next_run = next_cron_run_ms(task.cron, now)
                if next_run and next_run <= now + 1000:
                    await on_fire(task)
                    if not task.recurring:
                        self.delete_task(task.id)
            await asyncio.sleep(10)
    
    def stop(self) -> None:
        self._running = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value


_cron_scheduler: CronScheduler | None = None


def get_cron_scheduler() -> CronScheduler:
    global _cron_scheduler
    if _cron_scheduler is None:
        _cron_scheduler = CronScheduler()
    return _cron_scheduler


async def cron_create(
    cron: str,
    prompt: str,
    recurring: bool = True,
    durable: bool = False,
) -> dict:
    scheduler = get_cron_scheduler()
    scheduler.enabled = True
    
    task_id = scheduler.add_task(cron, prompt, recurring, durable)
    
    return {
        "id": task_id,
        "humanSchedule": cron_to_human(cron),
        "recurring": recurring,
        "durable": durable,
    }


async def cron_delete(task_id: str) -> dict:
    scheduler = get_cron_scheduler()
    success = scheduler.delete_task(task_id)
    return {"success": success}


async def cron_list() -> list[dict]:
    scheduler = get_cron_scheduler()
    return [
        {
            "id": t.id,
            "cron": t.cron,
            "prompt": t.prompt,
            "recurring": t.recurring,
            "durable": t.durable,
        }
        for t in scheduler.list_tasks()
    ]
