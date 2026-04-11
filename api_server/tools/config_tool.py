"""
Config Tool — get and set configuration values.
"""
import json
from pathlib import Path
from typing import Any, Dict

from .types import ToolDef, ToolContext, ToolResult


# Default config paths
DEFAULT_CONFIG_DIR = Path.home() / ".claude"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


async def execute_config_get(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Get configuration value."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    key = args.get('key')
    
    if not key:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="key is required",
            is_error=True,
        )
    
    # Try to read from default config file
    if DEFAULT_CONFIG_FILE.exists():
        try:
            config = json.loads(DEFAULT_CONFIG_FILE.read_text())
            
            value = config.get(key)
            if value is None:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Config key '{key}' not found",
                    is_error=True,
                )
            return ToolResult(
                tool_call_id=tool_call_id,
                output=f"{key} = {json.dumps(value)}",
                is_error=False,
            )
        except json.JSONDecodeError:
            return ToolResult(
                tool_call_id=tool_call_id,
                output="Config file is corrupted (invalid JSON)",
                is_error=True,
            )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No config file found",
            is_error=True,
        )


async def execute_config_set(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Set configuration value."""
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    key = args.get('key')
    value = args.get('value')
    
    if key is None or value is None:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Both 'key' and 'value' are required",
            is_error=True,
        )
    
    # Read existing config
    config = {}
    if DEFAULT_CONFIG_FILE.exists():
        try:
            config = json.loads(DEFAULT_CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            config = {}
    
    # Update config
    config[key] = value
    
    # Ensure directory exists
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write back
    try:
        DEFAULT_CONFIG_FILE.write_text(json.dumps(config, indent=2))
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Set {key} = {json.dumps(value)}",
            is_error=False,
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Failed to write config: {e}",
            is_error=True,
        )


TOOL_CONFIG_GET = ToolDef(
    name="config_get",
    description="Get configuration value",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
        },
        "required": ["key"]
    },
    is_read_only=True,
    risk_level="low",
    execute=execute_config_get,
)


TOOL_CONFIG_SET = ToolDef(
    name="config_set",
    description="Set configuration value",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"]
    },
    is_read_only=False,
    risk_level="medium",
    execute=execute_config_set,
)


__all__ = ["TOOL_CONFIG_GET", "TOOL_CONFIG_SET"]