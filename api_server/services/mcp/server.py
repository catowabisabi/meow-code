"""MCP server implementation for api_server."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_SERVER_START_TIMEOUT_MS = 30000
DEFAULT_SERVER_STOP_TIMEOUT_MS = 10000
DEFAULT_RESTART_BACKOFF_MS = 1000
MAX_RESTART_BACKOFF_MS = 30000


class MCPServerError(Exception):
    """Raised when MCP server operation fails."""
    pass


class MCPServerStartError(MCPServerError):
    """Raised when MCP server fails to start."""
    pass


class MCPServerStopError(MCPServerError):
    """Raised when MCP server fails to stop."""
    pass


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    timeout_ms: int = DEFAULT_SERVER_START_TIMEOUT_MS


@dataclass
class MCPServer:
    """
    MCP server instance.
    Manages lifecycle of an MCP server process.
    """

    name: str
    config: MCPServerConfig
    process: Optional[asyncio.subprocess.Process] = None

    _running: bool = field(default=False)
    _start_time: float = field(default=0)
    _restart_count: int = field(default=0)
    _last_error: Optional[str] = field(default=None)

    on_output: Optional[Callable[[str], None]] = None
    on_error: Optional[Callable[[str], None]] = None
    on_exit: Optional[Callable[[int], None]] = None

    async def start(self) -> None:
        """
        Start the MCP server.
        """
        if self._running:
            logger.warning(f"Server '{self.name}' is already running")
            return

        logger.info(f"Starting MCP server '{self.name}'")

        try:
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                env=self.config.env,
                cwd=self.config.cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._running = True
            self._start_time = time.time()
            self._restart_count = 0

            asyncio.create_task(self._read_stdout())
            asyncio.create_task(self._read_stderr())

            logger.info(f"MCP server '{self.name}' started with PID {self.process.pid}")

        except Exception as e:
            self._running = False
            self._last_error = str(e)
            raise MCPServerStartError(f"Failed to start '{self.name}': {e}") from e

    async def _read_stdout(self) -> None:
        """Read stdout from server process."""
        if not self.process or not self.process.stdout:
            return

        try:
            while self._running and self.process:
                line = await self.process.stdout.readline()
                if not line:
                    break
                output = line.decode("utf-8").rstrip()
                if output and self.on_output:
                    self.on_output(output)
        except Exception as e:
            if self._running:
                logger.error(f"Error reading stdout from '{self.name}': {e}")

    async def _read_stderr(self) -> None:
        """Read stderr from server process."""
        if not self.process or not self.process.stderr:
            return

        try:
            while self._running and self.process:
                line = await self.process.stderr.readline()
                if not line:
                    break
                output = line.decode("utf-8").rstrip()
                if output:
                    if self.on_error:
                        self.on_error(output)
                    else:
                        logger.debug(f"[{self.name} stderr] {output}")
        except Exception as e:
            if self._running:
                logger.error(f"Error reading stderr from '{self.name}': {e}")

    async def stop(self, timeout_ms: int = DEFAULT_SERVER_STOP_TIMEOUT_MS) -> None:
        """
        Stop the MCP server.
        """
        if not self._running:
            logger.warning(f"Server '{self.name}' is not running")
            return

        logger.info(f"Stopping MCP server '{self.name}'")

        if not self.process:
            self._running = False
            return

        try:
            self.process.terminate()
            try:
                await asyncio.wait_for(
                    self.process.wait(),
                    timeout=timeout_ms / 1000
                )
            except asyncio.TimeoutError:
                logger.warning(f"Server '{self.name}' did not stop gracefully, killing")
                self.process.kill()
                await self.process.wait()

            exit_code = self.process.returncode
            if self.on_exit:
                self.on_exit(exit_code)

            logger.info(f"MCP server '{self.name}' stopped with exit code {exit_code}")

        except Exception as e:
            self._last_error = str(e)
            raise MCPServerStopError(f"Failed to stop '{self.name}': {e}") from e

        finally:
            self._running = False
            self.process = None

    async def restart(
        self,
        backoff_ms: int = DEFAULT_RESTART_BACKOFF_MS,
        max_backoff_ms: int = MAX_RESTART_BACKOFF_MS,
    ) -> None:
        """
        Restart the MCP server with exponential backoff.
        """
        self._restart_count += 1

        if self._running:
            await self.stop()

        delay_ms = min(backoff_ms * (2 ** (self._restart_count - 1)), max_backoff_ms)
        logger.info(f"Restarting '{self.name}' after {delay_ms}ms delay")
        await asyncio.sleep(delay_ms / 1000)

        await self.start()

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running and self.process is not None

    @property
    def uptime(self) -> float:
        """Get server uptime in seconds."""
        if not self._start_time:
            return 0
        return time.time() - self._start_time

    @property
    def restart_count(self) -> int:
        """Get number of restarts."""
        return self._restart_count


async def start_server(config: MCPServerConfig) -> MCPServer:
    """
    Start an MCP server with the given configuration.
    """
    server = MCPServer(name=config.name, config=config)
    await server.start()
    return server


async def stop_server(server: MCPServer, timeout_ms: int = DEFAULT_SERVER_STOP_TIMEOUT_MS) -> None:
    """
    Stop an MCP server.
    """
    await server.stop(timeout_ms=timeout_ms)


async def restart_server(
    server: MCPServer,
    backoff_ms: int = DEFAULT_RESTART_BACKOFF_MS,
    max_backoff_ms: int = MAX_RESTART_BACKOFF_MS,
) -> None:
    """
    Restart an MCP server with exponential backoff.
    """
    await server.restart(backoff_ms=backoff_ms, max_backoff_ms=max_backoff_ms)


class MCPServerRegistry:
    """
    Registry for managing multiple MCP server instances.
    """

    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def add(self, name: str, server: MCPServer) -> None:
        """Add a server to the registry."""
        if name in self._servers:
            logger.warning(f"Server '{name}' already exists, replacing")
        self._servers[name] = server

    def get(self, name: str) -> Optional[MCPServer]:
        """Get a server by name."""
        return self._servers.get(name)

    def remove(self, name: str) -> Optional[MCPServer]:
        """Remove a server from the registry."""
        return self._servers.pop(name, None)

    def list(self) -> List[str]:
        """List all registered server names."""
        return list(self._servers.keys())

    async def start_all(self) -> None:
        """Start all registered servers."""
        for server in self._servers.values():
            if not server.is_running:
                try:
                    await server.start()
                except Exception as e:
                    logger.error(f"Failed to start server '{server.name}': {e}")

    async def stop_all(self, timeout_ms: int = DEFAULT_SERVER_STOP_TIMEOUT_MS) -> None:
        """Stop all registered servers."""
        for name, server in list(self._servers.items()):
            try:
                await server.stop(timeout_ms=timeout_ms)
            except Exception as e:
                logger.error(f"Failed to stop server '{name}': {e}")

    async def restart_all(
        self,
        backoff_ms: int = DEFAULT_RESTART_BACKOFF_MS,
        max_backoff_ms: int = MAX_RESTART_BACKOFF_MS,
    ) -> None:
        """Restart all registered servers."""
        for server in self._servers.values():
            try:
                await server.restart(backoff_ms=backoff_ms, max_backoff_ms=max_backoff_ms)
            except Exception as e:
                logger.error(f"Failed to restart server '{server.name}': {e}")


_server_registry: Optional[MCPServerRegistry] = None


def get_server_registry() -> MCPServerRegistry:
    """Get the global server registry."""
    global _server_registry
    if _server_registry is None:
        _server_registry = MCPServerRegistry()
    return _server_registry
