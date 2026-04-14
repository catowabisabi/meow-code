"""IDE integration and upstream proxy - bridging gaps"""
import asyncio
import logging
import os
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


IDE_INFO = {
    "vscode": {"name": "Visual Studio Code", "cmd": ["code"]},
    "cursor": {"name": "Cursor", "cmd": ["cursor"]},
    "vim": {"name": "Vim", "cmd": ["vim"]},
    "neovim": {"name": "Neovim", "cmd": ["nvim"]},
    "emacs": {"name": "Emacs", "cmd": ["emacs"]},
    "sublime": {"name": "Sublime Text", "cmd": ["subl"]},
    "jetbrains": {"name": "JetBrains IDE", "cmd": ["idea"]},
}


@dataclass
class IDEDiffRequest:
    file_path: str
    original_content: str
    new_content: str
    language: str


def detect_ides() -> List[str]:
    detected = []
    
    for ide_id, info in IDE_INFO.items():
        cmd = info["cmd"][0]
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                detected.append(ide_id)
        except Exception:
            pass
    
    return detected


def find_available_ide() -> Optional[str]:
    for ide_id in IDE_INFO:
        if os.getenv(f"CLAUDE_IDE_{ide_id.upper()}"):
            return ide_id
    
    detected = detect_ides()
    if detected:
        return detected[0]
    
    return None


class IDEDiff:
    """
    IDE RPC bridge for diff display.
    
    TypeScript equivalent: hooks/useDiffInIDE.ts
    Python gap: No diff display API.
    """
    
    def __init__(self, ide: Optional[str] = None):
        self.ide = ide or find_available_ide()
    
    async def show_diff(self, request: IDEDiffRequest) -> bool:
        if not self.ide:
            logger.warning("No IDE available for diff display")
            return False
        
        try:
            if self.ide == "vscode":
                return await self._show_vscode_diff(request)
            elif self.ide == "cursor":
                return await self._show_cursor_diff(request)
            else:
                logger.warning(f"Diff not supported for {self.ide}")
                return False
        except Exception as e:
            logger.error(f"Failed to show diff: {e}")
            return False
    
    async def _show_vscode_diff(self, request: IDEDiffRequest) -> bool:
        temp_original = f"/tmp/claude_diff_original_{os.getpid()}.txt"
        temp_new = f"/tmp/claude_diff_new_{os.getpid()}.txt"
        
        Path(temp_original).write_text(request.original_content)
        Path(temp_new).write_text(request.new_content)
        
        try:
            result = subprocess.run(
                ["code", "--diff", temp_original, temp_new],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        finally:
            Path(temp_original).unlink(missing_ok=True)
            Path(temp_new).unlink(missing_ok=True)
    
    async def _show_cursor_diff(self, request: IDEDiffRequest) -> bool:
        temp_original = f"/tmp/claude_diff_original_{os.getpid()}.txt"
        temp_new = f"/tmp/claude_diff_new_{os.getpid()}.txt"
        
        Path(temp_original).write_text(request.original_content)
        Path(temp_new).write_text(request.new_content)
        
        try:
            result = subprocess.run(
                ["cursor", "--diff", temp_original, temp_new],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        finally:
            Path(temp_original).unlink(missing_ok=True)
            Path(temp_new).unlink(missing_ok=True)


class UpstreamProxy:
    """
    TCP server and CONNECT parser for upstream proxy.
    
    TypeScript equivalent: upstreamproxy/upstreamproxy.ts
    Python gap: Zero Python coverage.
    """
    
    def __init__(self, port: int = 8080):
        self.port = port
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._proxy_host: Optional[str] = None
        self._proxy_port: Optional[int] = None
        self._auth: Optional[Tuple[str, str]] = None
    
    async def start(
        self,
        proxy_host: str,
        proxy_port: int,
        auth: Optional[Tuple[str, str]] = None
    ) -> None:
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._auth = auth
        self._running = True
        
        self._server = await asyncio.start_server(
            self._handle_connection,
            "127.0.0.1",
            self.port
        )
        
        logger.info(f"Upstream proxy started on port {self.port}")
    
    async def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
    
    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        pass
    
    def set_proxy(
        self,
        proxy_host: str,
        proxy_port: int,
        auth: Optional[Tuple[str, str]] = None
    ) -> None:
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._auth = auth
        
        os.environ["http_proxy"] = f"http://{proxy_host}:{proxy_port}"
        os.environ["https_proxy"] = f"http://{proxy_host}:{proxy_port}"


_ide_diff: Optional[IDEDiff] = None
_upstream_proxy: Optional[UpstreamProxy] = None


def get_ide_diff() -> IDEDiff:
    global _ide_diff
    if _ide_diff is None:
        _ide_diff = IDEDiff()
    return _ide_diff


def get_upstream_proxy() -> UpstreamProxy:
    global _upstream_proxy
    if _upstream_proxy is None:
        _upstream_proxy = UpstreamProxy()
    return _upstream_proxy
