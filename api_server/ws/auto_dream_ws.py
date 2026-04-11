"""
WebSocket handler for auto dream progress updates.

Pushes periodic updates to connected clients about dream consolidation progress.
"""
from fastapi import WebSocket, WebSocketDisconnect

from ..services.auto_dream import get_dream_task


async def auto_dream_websocket(websocket: WebSocket, task_id: str) -> None:
    """
    WebSocket handler for auto dream progress updates.
    
    Args:
        websocket: WebSocket connection.
        task_id: Dream task identifier to monitor.
    """
    await websocket.accept()
    
    try:
        while True:
            task = await get_dream_task(task_id)
            if task is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "Task not found",
                })
                break
            
            await websocket.send_json({
                "type": "dream_progress",
                "task_id": task.task_id,
                "status": task.status,
                "phase": task.phase,
                "sessions_reviewing": task.sessions_reviewing,
                "turns_count": len(task.turns),
                "files_touched": task.files_touched,
            })
            
            if task.status in ("completed", "failed", "killed"):
                break
            
            import asyncio
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
