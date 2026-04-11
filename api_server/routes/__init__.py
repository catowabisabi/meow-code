from api_server.routes.history import router as history_router
from api_server.routes.sessions import router as sessions_router
from api_server.routes.models import router as models_router
from api_server.routes.files import router as files_router
from api_server.routes.shell import router as shell_router
from api_server.routes.tools import router as tools_router
from api_server.routes.memory import router as memory_router
from api_server.routes.skills import router as skills_router
from api_server.routes.database import router as database_router
from api_server.routes.notion import router as notion_router
from api_server.routes.settings import router as settings_router
from api_server.routes.commands import router as commands_router
from api_server.routes.agents import router as agents_router
from api_server.routes.agents_config import router as agents_config_router
from api_server.routes.permissions import router as permissions_router
from api_server.routes.privacy_settings import router as privacy_settings_router
from api_server.routes.hooks import router as hooks_router
from api_server.routes.bridge import router as bridge_router
from api_server.routes.tags import router as tags_router
from api_server.routes.export import router as export_router
from api_server.routes.bootstrap import router as bootstrap_router
from api_server.routes.admin_requests import router as admin_requests_router
from api_server.routes.container import router as container_router

__all__ = [
    "history_router",
    "sessions_router",
    "models_router",
    "files_router",
    "shell_router",
    "tools_router",
    "memory_router",
    "skills_router",
    "database_router",
    "notion_router",
    "settings_router",
    "commands_router",
    "agents_router",
    "agents_config_router",
    "permissions_router",
    "privacy_settings_router",
    "hooks_router",
    "bridge_router",
    "tags_router",
    "export_router",
    "bootstrap_router",
    "admin_requests_router",
    "container_router",
]