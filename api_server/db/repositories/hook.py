from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from api_server.models.hook import Hook
from api_server.models.hook_execution import HookExecution

class HookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Dict[str, Any]:
        hook = Hook(**kwargs)
        self.db.add(hook)
        await self.db.commit()
        await self.db.refresh(hook)
        return self._to_dict(hook)

    async def get_by_id(self, hook_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(Hook).where(Hook.id == hook_id)
        )
        hook = result.scalar_one_or_none()
        return self._to_dict(hook) if hook else None

    async def get_all(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(Hook)
        if user_id:
            query = query.where(Hook.user_id == user_id)
        result = await self.db.execute(query)
        hooks = result.scalars().all()
        return [self._to_dict(h) for h in hooks]

    async def update(self, hook_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        await self.db.execute(
            update(Hook).where(Hook.id == hook_id).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_by_id(hook_id)

    async def delete(self, hook_id: str) -> bool:
        result = await self.db.execute(
            delete(Hook).where(Hook.id == hook_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def exists(self, hook_id: str) -> bool:
        result = await self.db.execute(
            select(Hook.id).where(Hook.id == hook_id)
        )
        return result.scalar_one_or_none() is not None

    def _to_dict(self, hook: Hook) -> Dict[str, Any]:
        return {
            "id": hook.id,
            "name": hook.name,
            "trigger_type": hook.trigger_type,
            "hook_type": hook.hook_type,
            "config": hook.config or {},
            "code": hook.code,
            "is_active": hook.is_active,
            "user_id": hook.user_id,
            "created_at": hook.created_at.isoformat() if hook.created_at else None,
            "updated_at": hook.updated_at.isoformat() if hook.updated_at else None,
        }

class HookExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Dict[str, Any]:
        execution = HookExecution(**kwargs)
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return self._to_dict(execution)

    async def get_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(HookExecution).where(HookExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        return self._to_dict(execution) if execution else None

    async def get_by_hook_id(self, hook_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(HookExecution)
            .where(HookExecution.hook_id == hook_id)
            .order_by(HookExecution.created_at.desc())
        )
        executions = result.scalars().all()
        return [self._to_dict(e) for e in executions]

    async def update_status(
        self,
        execution_id: str,
        status: str,
        error_message: Optional[str] = None,
        result: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        from datetime import datetime
        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message
        if result:
            update_data["result"] = result
        if status == "completed":
            update_data["completed_at"] = str(int(datetime.now().timestamp()))
        
        await self.db.execute(
            update(HookExecution)
            .where(HookExecution.id == execution_id)
            .values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(execution_id)

    def _to_dict(self, execution: HookExecution) -> Dict[str, Any]:
        return {
            "id": execution.id,
            "hook_id": execution.hook_id,
            "status": execution.status,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "duration_ms": execution.duration_ms,
            "error_message": execution.error_message,
            "result": execution.result,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
            "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
        }