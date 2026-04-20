from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import time

from .routes import (
    sessions_router,
    models_router,
    files_router,
    shell_router,
    tools_router,
    memory_router,
    skills_router,
    database_router,
    notion_router,
    settings_router,
    commands_router,
    agents_router,
    agents_config_router,
    permissions_router,
    privacy_settings_router,
    hooks_router,
    bridge_router,
    tags_router,
    export_router,
    bootstrap_router,
    admin_requests_router,
    history_router,
    container_router,
    mcp_router,
)
from .db.settings_db import init_db, init_issues_db, get_db, get_issues_db
from .ws.chat import websocket_endpoint
from .ws.agent_summary_ws import agent_summary_websocket
from .ws.bridge_ws import bridge_websocket
from .tools.register import register_all_tools


WEBUI_DIST = Path(__file__).parent.parent / "webui" / "client" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api_server.tools.register import register_all_tools
    register_all_tools()
    init_db()
    init_issues_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Cato API Server", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── WebSocket routes FIRST — must be before any HTTP catch-all ──
    app.add_api_websocket_route("/ws/chat", websocket_endpoint)
    app.add_api_websocket_route("/ws/agent-summary/{agent_id}", agent_summary_websocket)
    app.add_api_websocket_route("/ws/bridge/{session_id}", bridge_websocket)

    app.include_router(history_router, prefix="/api", tags=["history"])
    app.include_router(container_router, prefix="/api", tags=["container"])
    app.include_router(sessions_router, prefix="/api", tags=["sessions"])
    app.include_router(models_router, prefix="/api", tags=["models"])
    app.include_router(files_router, prefix="/api", tags=["files"])
    app.include_router(shell_router, prefix="/api", tags=["shell"])
    app.include_router(tools_router, prefix="/api", tags=["tools"])
    app.include_router(memory_router, prefix="/api", tags=["memory"])
    app.include_router(skills_router, prefix="/api", tags=["skills"])
    app.include_router(database_router, prefix="/api", tags=["database"])
    app.include_router(notion_router, prefix="/api", tags=["notion"])
    app.include_router(settings_router, prefix="/api", tags=["settings"])
    app.include_router(commands_router, prefix="/api", tags=["commands"])
    app.include_router(agents_router, prefix="/api", tags=["agents"])
    app.include_router(agents_config_router, prefix="/api", tags=["agents-config"])
    app.include_router(permissions_router, prefix="/api", tags=["permissions"])
    app.include_router(privacy_settings_router, prefix="/api", tags=["privacy-settings"])
    app.include_router(hooks_router, prefix="/api", tags=["hooks"])
    app.include_router(bridge_router, prefix="/api", tags=["bridge"])
    app.include_router(tags_router, prefix="/api", tags=["tags"])
    app.include_router(export_router, prefix="/api", tags=["export"])
    app.include_router(bootstrap_router, prefix="/api", tags=["bootstrap"])
    app.include_router(admin_requests_router, prefix="/api", tags=["admin-requests"])
    app.include_router(mcp_router, prefix="/api", tags=["mcp"])

    @app.get("/health")
    async def health():
        checks = []
        overall_ok = True
        
        start = time.time()
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            db_ms = round((time.time() - start) * 1000, 1)
            checks.append({"name": "sqlite_db", "status": "ok", "latency_ms": db_ms})
        except Exception as e:
            checks.append({"name": "sqlite_db", "status": "error", "error": str(e)})
            overall_ok = False
        
        start = time.time()
        try:
            issues_conn = get_issues_db()
            cursor = issues_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'open'")
            open_count = cursor.fetchone()[0]
            issues_conn.close()
            issues_ms = round((time.time() - start) * 1000, 1)
            checks.append({"name": "issues_db", "status": "ok", "open_issues": open_count, "latency_ms": issues_ms})
        except Exception as e:
            checks.append({"name": "issues_db", "status": "error", "error": str(e)})
            overall_ok = False
        
        if overall_ok:
            return {"status": "ok", "checks": checks, "timestamp": time.time()}
        else:
            return {"status": "degraded", "checks": checks, "timestamp": time.time()}

    if WEBUI_DIST.exists():
        # Serve /assets/* as static files
        app.mount("/assets", StaticFiles(directory=str(WEBUI_DIST / "assets")), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(WEBUI_DIST / "index.html")

        @app.get("/{path:path}")
        async def serve_static(request: Request, path: str):
            # Skip WebSocket upgrade requests
            if request.headers.get("upgrade", "").lower() == "websocket":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            if path.startswith("api"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            file_path = WEBUI_DIST / path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(WEBUI_DIST / "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7778)
