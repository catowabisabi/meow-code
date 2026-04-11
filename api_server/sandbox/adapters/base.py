"""
Base sandbox adapter interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import shlex


@dataclass
class SandboxCheck:
    """Result of a sandbox availability check."""
    is_available: bool
    errors: list[str]
    warnings: list[str]


class SandboxAdapter(ABC):
    """
    Abstract base class for platform-specific sandbox adapters.
    
    Implementations must provide:
    - is_available(): Check if sandbox can be used
    - get_platform_name(): Return platform identifier
    - wrap_command(): Wrap a command with sandbox options
    - get_sandbox_profile(): Get sandbox profile/command
    """
    
    @abstractmethod
    def is_available(self) -> SandboxCheck:
        """
        Check if this sandbox adapter is available on the system.
        
        Returns SandboxCheck with is_available=True if the adapter
        can be used, False otherwise with list of errors.
        """
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name (e.g., 'linux', 'macos', 'windows')."""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the sandbox adapter (setup, validation, etc.)."""
        pass
    
    def wrap_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
    ) -> str:
        """
        Wrap a command with sandbox invocation.
        
        Args:
            command: The shell command to wrap
            working_dir: Working directory (optional)
            uid: User ID to run as (optional)
            gid: Group ID to run as (optional)
        
        Returns:
            The wrapped command string ready for shell execution.
        """
        raise NotImplementedError("Subclass must implement wrap_command")
    
    def get_sandbox_profile(self) -> str:
        """
        Get the sandbox profile/configuration for this adapter.
        
        This is used for documentation and debugging purposes.
        """
        return ""
    
    def is_command_excluded(self, command: str, excluded_commands: list[str]) -> bool:
        """
        Check if a command matches any of the exclusion patterns.
        
        Args:
            command: The full command string
            excluded_commands: List of commands/patterns to exclude
        
        Returns:
            True if the command should bypass sandbox
        """
        if not excluded_commands:
            return False
        
        try:
            parts = shlex.split(command)
            if not parts:
                return False
            
            cmd_name = parts[0]
            
            for excluded in excluded_commands:
                if excluded == cmd_name:
                    return True
                if command.startswith(excluded):
                    return True
                if cmd_name == excluded:
                    return True
            
            return False
        except ValueError:
            return False
    
    def get_command_name(self, command: str) -> str:
        """Extract the command name from a command string."""
        try:
            parts = shlex.split(command)
            return parts[0] if parts else ""
        except ValueError:
            return command.split()[0] if command else ""


class SandboxAdapterFactory:
    """Factory for creating appropriate sandbox adapters."""
    
    _adapters: dict[str, type] = {}
    
    @classmethod
    def register(cls, platform: str, adapter_class: type):
        """Register an adapter for a platform."""
        cls._adapters[platform] = adapter_class
    
    @classmethod
    def get_adapter(cls, platform: str) -> Optional[type]:
        """Get the adapter class for a platform."""
        return cls._adapters.get(platform)
    
    @classmethod
    def create(cls, platform: str) -> SandboxAdapter:
        """Create an adapter instance for a platform."""
        adapter_class = cls._adapters.get(platform)
        if adapter_class is None:
            from .noop import NoopAdapter
            adapter_class = NoopAdapter
        return adapter_class()
