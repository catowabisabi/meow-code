"""
Sandboxed shell executor - integrates sandbox with shell execution.
"""

import asyncio
import logging
import shlex
from typing import Callable, Optional

from ..services.sandbox.shell_security import validate_shell_command
from ..tools.shell import execute_shell_command, ShellInput, ToolResult
from .config import SandboxConfig
from .exceptions import SandboxUnavailable, SandboxViolation
from .path_restrictions import PathRestrictions
from . import get_sandbox_adapter


logger = logging.getLogger(__name__)


class SandboxedShellExecutor:
    """
    Shell executor with sandbox integration.
    
    Wraps shell command execution with sandbox restrictions
    when available and configured.
    """
    
    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        adapter=None,
    ):
        self.config = config or SandboxConfig.default()
        self.adapter = adapter or get_sandbox_adapter()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the sandbox adapter."""
        if self._initialized:
            return
        
        check = self.adapter.is_available()
        if not check.is_available:
            if self.config.fail_if_unavailable:
                raise SandboxUnavailable(
                    f"Sandbox required but unavailable: {', '.join(check.errors)}",
                    platform=self.adapter.get_platform_name(),
                    errors=check.errors,
                )
            logger.warning(
                f"Sandbox unavailable, running without isolation: {check.errors}"
            )
        
        for warning in check.warnings:
            logger.warning(f"Sandbox warning: {warning}")
        
        await self.adapter.initialize()
        self._initialized = True
    
    async def execute(
        self,
        input_data: ShellInput,
        cwd: Optional[str] = None,
        abort_signal: Optional[asyncio.Event] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> ToolResult:
        """
        Execute a shell command with sandbox restrictions.
        
        Args:
            input_data: ShellInput with command, timeout, shell, cwd
            cwd: Working directory (defaults to input_data.cwd or current)
            abort_signal: Optional event to check for abortion
            on_progress: Optional callback for streaming output
        
        Returns:
            ToolResult with execution output
        """
        await self.initialize()
        
        command = input_data.command
        
        security_result = validate_shell_command(command, self.config, cwd)
        if not security_result["allowed"]:
            msg = security_result.get("message", "Security validation failed")
            if self.config.fail_on_violation:
                raise SandboxViolation(
                    f"Shell security validation failed: {msg}",
                    restriction_type="security",
                    path=security_result.get("blocked_path", ""),
                )
            logger.warning(f"Shell security validation warning: {msg}")
        
        if self._is_excluded(command):
            logger.debug(f"Command excluded from sandbox: {self._get_command_name(command)}")
            return await self._execute_unsafe(input_data, cwd, abort_signal, on_progress)
        
        allowed, reason = self._check_path_access(command)
        if not allowed:
            if self.config.fail_on_violation:
                raise SandboxViolation(
                    f"Path access denied: {reason}",
                    restriction_type="filesystem",
                    path=reason,
                )
            logger.warning(f"Sandbox path violation: {reason}")
        
        wrapped_command = self.adapter.wrap_command(
            command,
            working_dir=input_data.cwd or cwd,
        )
        
        sandboxed_input = ShellInput(
            command=wrapped_command,
            timeout=input_data.timeout,
            shell=input_data.shell,
            cwd=input_data.cwd or cwd,
        )
        
        result = await self._execute_unsafe(sandboxed_input, cwd, abort_signal, on_progress)
        
        result.metadata["sandbox_enabled"] = True
        result.metadata["sandbox_adapter"] = self.adapter.get_platform_name()
        
        return result
    
    async def _execute_unsafe(
        self,
        input_data: ShellInput,
        cwd: Optional[str] = None,
        abort_signal: Optional[asyncio.Event] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> ToolResult:
        """Execute without sandbox (for excluded commands or fallback)."""
        return await execute_shell_command(
            input_data,
            cwd=cwd,
            abort_signal=abort_signal,
            on_progress=on_progress,
        )
    
    def _is_excluded(self, command: str) -> bool:
        """Check if command should bypass sandbox."""
        if not self.config.excluded_commands:
            return False
        
        cmd_name = self._get_command_name(command)
        
        for excluded in self.config.excluded_commands:
            if cmd_name == excluded:
                return True
            if command.startswith(excluded):
                return True
            if excluded in command.split():
                return True
        
        return False
    
    def _get_command_name(self, command: str) -> str:
        """Extract the command name from a command string."""
        try:
            parts = shlex.split(command)
            return parts[0] if parts else ""
        except ValueError:
            return command.split()[0] if command else ""
    
    def _check_path_access(self, command: str) -> tuple[bool, str]:
        """
        Check if command accesses allowed paths.
        
        Returns (allowed, reason).
        """
        path_restrictions = PathRestrictions(
            allow_read=self.config.filesystem.allow_read,
            deny_read=self.config.filesystem.deny_read,
            allow_write=self.config.filesystem.allow_write,
            deny_write=self.config.filesystem.deny_write,
        )
        
        return path_restrictions.check_command_access(command)
    
    async def execute_simple(
        self,
        command: str,
        timeout: int = 120000,
        shell: str = "auto",
        cwd: Optional[str] = None,
    ) -> ToolResult:
        """
        Simple synchronous-style execution with sandbox.
        
        Convenience method for simpler use cases.
        """
        input_data = ShellInput(
            command=command,
            timeout=timeout,
            shell=shell,
            cwd=cwd,
        )
        
        return await self.execute(input_data, cwd=cwd)
    
    def get_status(self) -> dict:
        """Get current sandbox status."""
        check = self.adapter.is_available()
        return {
            "initialized": self._initialized,
            "adapter": self.adapter.get_platform_name(),
            "available": check.is_available,
            "errors": check.errors,
            "warnings": check.warnings,
            "config": {
                "filesystem_allow_read": self.config.filesystem.allow_read,
                "filesystem_deny_read": self.config.filesystem.deny_read,
                "filesystem_allow_write": self.config.filesystem.allow_write,
                "filesystem_deny_write": self.config.filesystem.deny_write,
                "excluded_commands": self.config.excluded_commands,
            },
        }
