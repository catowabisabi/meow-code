import asyncio
import re
from dataclasses import dataclass
from typing import Callable, Awaitable


@dataclass
class TeleportConfig:
    ssh_host: str | None = None
    ssh_port: int = 22
    ssh_user: str | None = None
    working_directory: str = "/"


async def check_teleport_available() -> bool:
    return False


async def connect_teleport(config: TeleportConfig) -> str:
    return ""


async def disconnect_teleport() -> None:
    pass


async def get_teleport_status() -> dict:
    return {"connected": False}
