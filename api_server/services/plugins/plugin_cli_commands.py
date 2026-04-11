"""
Plugin CLI commands for managing Claude Code plugins.

This module provides a command registry for plugin-specific CLI commands,
allowing plugins to register their own commands that can be invoked via CLI.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class CommandResult:
    """Result of executing a plugin CLI command."""
    success: bool
    message: str
    command_name: str
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PluginCLICommand:
    """Represents a plugin CLI command."""
    name: str
    description: str
    handler: Callable[..., CommandResult]


class PluginCLICommands:
    """Manages plugin CLI commands.
    
    Provides a registry for plugin-specific CLI commands that can be
    registered, looked up, listed, and executed.
    """
    
    def __init__(self) -> None:
        self._commands: dict[str, PluginCLICommand] = {}
    
    def register_command(self, command: PluginCLICommand) -> None:
        """Register a plugin CLI command.
        
        Args:
            command: The PluginCLICommand to register.
            
        Raises:
            ValueError: If a command with the same name is already registered.
        """
        if command.name in self._commands:
            raise ValueError(f"Command '{command.name}' is already registered")
        self._commands[command.name] = command
    
    def get_command(self, name: str) -> Optional[PluginCLICommand]:
        """Get a registered command by name.
        
        Args:
            name: The name of the command to retrieve.
            
        Returns:
            The PluginCLICommand if found, None otherwise.
        """
        return self._commands.get(name)
    
    def list_commands(self) -> list[PluginCLICommand]:
        """List all registered commands.
        
        Returns:
            A list of all registered PluginCLICommand objects.
        """
        return list(self._commands.values())
    
    def execute_command(self, name: str, args: dict) -> CommandResult:
        """Execute a plugin command by name.
        
        Args:
            name: The name of the command to execute.
            args: Dictionary of arguments to pass to the command handler.
            
        Returns:
            CommandResult indicating success or failure.
        """
        command = self._commands.get(name)
        if command is None:
            return CommandResult(
                success=False,
                message=f"Command '{name}' not found",
                command_name=name,
            )
        
        try:
            result = command.handler(args)
            if isinstance(result, CommandResult):
                return result
            return CommandResult(
                success=True,
                message="Command executed successfully",
                command_name=name,
                output=str(result),
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Command execution failed: {str(e)}",
                command_name=name,
                error=str(e),
            )
    
    def unregister_command(self, name: str) -> bool:
        """Unregister a command by name.
        
        Args:
            name: The name of the command to unregister.
            
        Returns:
            True if the command was unregistered, False if it wasn't found.
        """
        if name in self._commands:
            del self._commands[name]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()


# Default instance for module-level access
_default_commands: Optional[PluginCLICommands] = None


def get_plugin_cli_commands() -> PluginCLICommands:
    """Get the default PluginCLICommands instance."""
    global _default_commands
    if _default_commands is None:
        _default_commands = PluginCLICommands()
    return _default_commands


def register_plugin_command(
    name: str,
    description: str,
    handler: Callable[..., CommandResult],
) -> None:
    """Register a plugin CLI command with the default registry.
    
    Args:
        name: The name of the command.
        description: A description of what the command does.
        handler: The callable that handles the command execution.
    """
    command = PluginCLICommand(name=name, description=description, handler=handler)
    get_plugin_cli_commands().register_command(command)


def get_command(name: str) -> Optional[PluginCLICommand]:
    """Get a registered command from the default registry."""
    return get_plugin_cli_commands().get_command(name)


def list_commands() -> list[PluginCLICommand]:
    """List all registered commands from the default registry."""
    return get_plugin_cli_commands().list_commands()


def execute_plugin_command(name: str, args: dict) -> CommandResult:
    """Execute a plugin command from the default registry."""
    return get_plugin_cli_commands().execute_command(name, args)
