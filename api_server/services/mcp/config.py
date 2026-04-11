"""
Configuration management for MCP (Model Context Protocol) service.

Mirrors the TypeScript config.ts implementation from Claude Code.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from .mcp_types import (
    ConfigScope,
    McpHTTPServerConfig,
    McpJsonConfig,
    McpServerConfig,
    McpSSEServerConfig,
    McpStdioServerConfig,
    McpWebSocketServerConfig,
    ScopedMcpServerConfig,
)

logger = logging.getLogger(__name__)


CCR_PROXY_PATH_MARKERS = [
    "/v2/session_ingress/shttp/mcp/",
    "/v2/ccr-sessions/",
]


def get_enterprise_mcp_file_path() -> str:
    """Get the path to the managed MCP configuration file."""
    managed_path = os.environ.get("MCP_MANAGED_PATH", ".mcp-managed.json")
    return str(Path.cwd() / managed_path)


def get_project_mcp_file_path() -> str:
    """Get the path to the project MCP configuration file."""
    return str(Path.cwd() / ".mcp.json")


def get_global_mcp_file_path() -> str:
    """Get the path to the global MCP configuration file."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return str(Path(config_home) / "claude" / "mcp.json")


def add_scope_to_servers(
    servers: Dict[str, McpServerConfig] | None,
    scope: ConfigScope,
) -> Dict[str, ScopedMcpServerConfig]:
    """Add scope to server configs."""
    if not servers:
        return {}
    return {name: {**config, "scope": scope} for name, config in servers.items()}


def get_server_command_array(config: McpServerConfig) -> List[str] | None:
    """Extract command array from server config (stdio servers only)."""
    config_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
    if config_type is not None and config_type != "stdio":
        return None
    if isinstance(config, dict):
        command = config.get("command", "")
        args = config.get("args", [])
    else:
        command = getattr(config, "command", "")
        args = getattr(config, "args", [])
    return [command] + args


def command_arrays_match(a: List[str], b: List[str]) -> bool:
    """Check if two command arrays match exactly."""
    if len(a) != len(b):
        return False
    return all(val == b[idx] for idx, val in enumerate(a))


def get_server_url(config: McpServerConfig) -> str | None:
    """Extract URL from server config (remote servers only)."""
    if isinstance(config, dict):
        return config.get("url", None)
    return getattr(config, "url", None)


def unwrap_ccr_proxy_url(url: str) -> str:
    """Extract original vendor URL from CCR proxy URL if applicable."""
    if not any(marker in url for marker in CCR_PROXY_PATH_MARKERS):
        return url
    try:
        parsed = urlparse(url)
        original = parsed.params.get("mcp_url")
        return original or url
    except Exception:
        return url


def get_mcp_server_signature(config: McpServerConfig) -> str | None:
    """Compute a dedup signature for an MCP server config."""
    cmd = get_server_command_array(config)
    if cmd:
        return f"stdio:{json.dumps(cmd)}"
    url = get_server_url(config)
    if url:
        return f"url:{unwrap_ccr_proxy_url(url)}"
    return None


def dedup_plugin_mcp_servers(
    plugin_servers: Dict[str, ScopedMcpServerConfig],
    manual_servers: Dict[str, ScopedMcpServerConfig],
) -> Tuple[Dict[str, ScopedMcpServerConfig], List[Dict[str, str]]]:
    """
    Filter plugin MCP servers, dropping any whose signature matches
    a manually-configured server or an earlier-loaded plugin server.
    """
    manual_sigs: Dict[str, str] = {}
    for name, config in manual_servers.items():
        sig = get_mcp_server_signature(config)
        if sig and sig not in manual_sigs:
            manual_sigs[sig] = name

    servers: Dict[str, ScopedMcpServerConfig] = {}
    suppressed: List[Dict[str, str]] = []
    seen_plugin_sigs: Dict[str, str] = {}

    for name, config in plugin_servers.items():
        sig = get_mcp_server_signature(config)
        if sig is None:
            servers[name] = config
            continue
        manual_dup = manual_sigs.get(sig)
        if manual_dup is not None:
            logger.debug(f"Suppressing plugin MCP server '{name}': duplicates manually-configured '{manual_dup}'")
            suppressed.append({"name": name, "duplicate_of": manual_dup})
            continue
        plugin_dup = seen_plugin_sigs.get(sig)
        if plugin_dup is not None:
            logger.debug(f"Suppressing plugin MCP server '{name}': duplicates earlier plugin server '{plugin_dup}'")
            suppressed.append({"name": name, "duplicate_of": plugin_dup})
            continue
        seen_plugin_sigs[sig] = name
        servers[name] = config

    return servers, suppressed


def url_pattern_to_regex(pattern: str) -> re.Pattern:
    """Convert a URL pattern with wildcards to a RegExp."""
    escaped = re.escape(pattern)
    regex_str = escaped.replace(r"\*", ".*")
    return re.compile(f"^{regex_str}$")


def url_matches_pattern(url: str, pattern: str) -> bool:
    """Check if a URL matches a pattern with wildcard support."""
    return bool(url_pattern_to_regex(pattern).match(url))


def parse_mcp_config(
    config_object: Any,
    expand_vars: bool = True,
    scope: ConfigScope = ConfigScope.LOCAL,
) -> Tuple[Optional[McpJsonConfig], List[Dict[str, Any]]]:
    """
    Parse and validate an MCP configuration object.

    Returns tuple of (config, errors).
    """
    errors: List[Dict[str, Any]] = []

    if not isinstance(config_object, dict):
        errors.append({
            "path": "",
            "message": "Configuration must be an object",
            "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
        })
        return None, errors

    mcp_servers = config_object.get("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        errors.append({
            "path": "mcpServers",
            "message": "mcpServers must be an object",
            "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
        })
        return None, errors

    validated_servers: Dict[str, McpServerConfig] = {}

    for name, server_config in mcp_servers.items():
        validated_config, config_errors = _validate_server_config(
            name, server_config, scope, expand_vars
        )
        if config_errors:
            errors.extend(config_errors)
        if validated_config:
            validated_servers[name] = validated_config

    return {"mcpServers": validated_servers}, errors


def _validate_server_config(
    name: str,
    config: Any,
    scope: ConfigScope,
    expand_vars: bool,
) -> Tuple[Optional[McpServerConfig], List[Dict[str, Any]]]:
    """Validate a single server configuration."""
    errors: List[Dict[str, Any]] = []

    if not isinstance(config, dict):
        errors.append({
            "path": f"mcpServers.{name}",
            "message": "Server config must be an object",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })
        return None, errors

    server_type = config.get("type")

    if server_type is None or server_type == "stdio":
        return _validate_stdio_config(name, config, scope, expand_vars)
    elif server_type == "sse":
        return _validate_sse_config(name, config, scope, expand_vars)
    elif server_type == "http":
        return _validate_http_config(name, config, scope, expand_vars)
    elif server_type == "ws":
        return _validate_ws_config(name, config, scope, expand_vars)
    else:
        errors.append({
            "path": f"mcpServers.{name}.type",
            "message": f"Unknown server type: {server_type}",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })
        return None, errors


def _validate_stdio_config(
    name: str,
    config: Dict[str, Any],
    scope: ConfigScope,
    expand_vars: bool,
) -> Tuple[Optional[McpStdioServerConfig], List[Dict[str, Any]]]:
    """Validate stdio server configuration."""
    errors: List[Dict[str, Any]] = []
    command = config.get("command", "")

    if not command or not isinstance(command, str):
        errors.append({
            "path": f"mcpServers.{name}.command",
            "message": "Command cannot be empty",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })
        return None, errors

    args = config.get("args", [])
    if not isinstance(args, list):
        errors.append({
            "path": f"mcpServers.{name}.args",
            "message": "args must be an array",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    env = config.get("env")
    if env is not None and not isinstance(env, dict):
        errors.append({
            "path": f"mcpServers.{name}.env",
            "message": "env must be an object",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    if errors:
        return None, errors

    return {
        "type": "stdio",
        "command": command,
        "args": args or [],
        "env": env,
    }, errors


def _validate_sse_config(
    name: str,
    config: Dict[str, Any],
    scope: ConfigScope,
    expand_vars: bool,
) -> Tuple[Optional[McpSSEServerConfig], List[Dict[str, Any]]]:
    """Validate SSE server configuration."""
    errors: List[Dict[str, Any]] = []
    url = config.get("url", "")

    if not url or not isinstance(url, str):
        errors.append({
            "path": f"mcpServers.{name}.url",
            "message": "URL cannot be empty",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    headers = config.get("headers")
    if headers is not None and not isinstance(headers, dict):
        errors.append({
            "path": f"mcpServers.{name}.headers",
            "message": "headers must be an object",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    oauth = config.get("oauth")
    if oauth is not None:
        oauth_errors = _validate_oauth_config(name, oauth, scope)
        errors.extend(oauth_errors)

    if errors:
        return None, errors

    return {
        "type": "sse",
        "url": url,
        "headers": headers,
        "headers_helper": config.get("headersHelper"),
        "oauth": oauth,
    }, errors


def _validate_http_config(
    name: str,
    config: Dict[str, Any],
    scope: ConfigScope,
    expand_vars: bool,
) -> Tuple[Optional[McpHTTPServerConfig], List[Dict[str, Any]]]:
    """Validate HTTP server configuration."""
    errors: List[Dict[str, Any]] = []
    url = config.get("url", "")

    if not url or not isinstance(url, str):
        errors.append({
            "path": f"mcpServers.{name}.url",
            "message": "URL cannot be empty",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    headers = config.get("headers")
    if headers is not None and not isinstance(headers, dict):
        errors.append({
            "path": f"mcpServers.{name}.headers",
            "message": "headers must be an object",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    oauth = config.get("oauth")
    if oauth is not None:
        oauth_errors = _validate_oauth_config(name, oauth, scope)
        errors.extend(oauth_errors)

    if errors:
        return None, errors

    return {
        "type": "http",
        "url": url,
        "headers": headers,
        "headers_helper": config.get("headersHelper"),
        "oauth": oauth,
    }, errors


def _validate_ws_config(
    name: str,
    config: Dict[str, Any],
    scope: ConfigScope,
    expand_vars: bool,
) -> Tuple[Optional[McpWebSocketServerConfig], List[Dict[str, Any]]]:
    """Validate WebSocket server configuration."""
    errors: List[Dict[str, Any]] = []
    url = config.get("url", "")

    if not url or not isinstance(url, str):
        errors.append({
            "path": f"mcpServers.{name}.url",
            "message": "URL cannot be empty",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    headers = config.get("headers")
    if headers is not None and not isinstance(headers, dict):
        errors.append({
            "path": f"mcpServers.{name}.headers",
            "message": "headers must be an object",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    if errors:
        return None, errors

    return {
        "type": "ws",
        "url": url,
        "headers": headers,
        "headers_helper": config.get("headersHelper"),
    }, errors


def _validate_oauth_config(
    name: str,
    oauth: Dict[str, Any],
    scope: ConfigScope,
) -> List[Dict[str, Any]]:
    """Validate OAuth configuration."""
    errors: List[Dict[str, Any]] = []

    client_id = oauth.get("clientId")
    if client_id is not None and not isinstance(client_id, str):
        errors.append({
            "path": f"mcpServers.{name}.oauth.clientId",
            "message": "clientId must be a string",
            "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
        })

    callback_port = oauth.get("callbackPort")
    if callback_port is not None:
        if not isinstance(callback_port, int) or callback_port <= 0:
            errors.append({
                "path": f"mcpServers.{name}.oauth.callbackPort",
                "message": "callbackPort must be a positive integer",
                "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
            })

    auth_server_metadata_url = oauth.get("authServerMetadataUrl")
    if auth_server_metadata_url is not None:
        if not isinstance(auth_server_metadata_url, str):
            errors.append({
                "path": f"mcpServers.{name}.oauth.authServerMetadataUrl",
                "message": "authServerMetadataUrl must be a string",
                "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
            })
        elif not auth_server_metadata_url.startswith("https://"):
            errors.append({
                "path": f"mcpServers.{name}.oauth.authServerMetadataUrl",
                "message": "authServerMetadataUrl must use https://",
                "mcp_error_metadata": {"scope": scope, "serverName": name, "severity": "fatal"},
            })

    return errors


def load_mcp_config_from_file(
    file_path: str,
    expand_vars: bool = True,
    scope: ConfigScope = ConfigScope.LOCAL,
) -> Tuple[Optional[McpJsonConfig], List[Dict[str, Any]]]:
    """Load and parse MCP configuration from a JSON file."""
    errors: List[Dict[str, Any]] = []

    if not os.path.exists(file_path):
        errors.append({
            "file": file_path,
            "path": "",
            "message": f"MCP config file not found: {file_path}",
            "suggestion": "Check that the file path is correct",
            "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
        })
        return None, errors

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            config_object = json.loads(content)
    except json.JSONDecodeError as e:
        errors.append({
            "file": file_path,
            "path": "",
            "message": f"MCP config is not valid JSON: {str(e)}",
            "suggestion": "Fix the JSON syntax errors in the file",
            "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
        })
        return None, errors
    except Exception as e:
        errors.append({
            "file": file_path,
            "path": "",
            "message": f"Failed to read file: {str(e)}",
            "suggestion": "Check file permissions and ensure the file exists",
            "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
        })
        return None, errors

    return parse_mcp_config(config_object, expand_vars, scope)


def get_mcp_configs_by_scope(
    scope: ConfigScope,
) -> Tuple[Dict[str, ScopedMcpServerConfig], List[Dict[str, Any]]]:
    """Get MCP configurations from a specific scope."""
    all_errors: List[Dict[str, Any]] = []
    servers: Dict[str, ScopedMcpServerConfig] = {}

    if scope == ConfigScope.PROJECT:
        project_path = get_project_mcp_file_path()
        if os.path.exists(project_path):
            config, errors = load_mcp_config_from_file(
                project_path, expand_vars=True, scope=scope
            )
            all_errors.extend(errors)
            if config and config.get("mcpServers"):
                servers = add_scope_to_servers(config["mcpServers"], scope)
    elif scope == ConfigScope.USER:
        global_path = get_global_mcp_file_path()
        if os.path.exists(global_path):
            config, errors = load_mcp_config_from_file(
                global_path, expand_vars=True, scope=scope
            )
            all_errors.extend(errors)
            if config and config.get("mcpServers"):
                servers = add_scope_to_servers(config["mcpServers"], scope)
    elif scope == ConfigScope.ENTERPRISE:
        enterprise_path = get_enterprise_mcp_file_path()
        if os.path.exists(enterprise_path):
            config, errors = load_mcp_config_from_file(
                enterprise_path, expand_vars=True, scope=scope
            )
            all_errors.extend(errors)
            if config and config.get("mcpServers"):
                servers = add_scope_to_servers(config["mcpServers"], scope)
    elif scope == ConfigScope.LOCAL:
        local_configs = os.environ.get("MCP_LOCAL_SERVERS")
        if local_configs:
            try:
                config_object = json.loads(local_configs)
                config, errors = parse_mcp_config(
                    config_object, expand_vars=True, scope=scope
                )
                all_errors.extend(errors)
                if config and config.get("mcpServers"):
                    servers = add_scope_to_servers(config["mcpServers"], scope)
            except json.JSONDecodeError:
                all_errors.append({
                    "path": "MCP_LOCAL_SERVERS",
                    "message": "Invalid JSON in MCP_LOCAL_SERVERS environment variable",
                    "mcp_error_metadata": {"scope": scope, "severity": "fatal"},
                })

    return servers, all_errors


def get_all_mcp_configs() -> Tuple[Dict[str, ScopedMcpServerConfig], List[Dict[str, Any]]]:
    """Get all MCP configurations across all scopes."""
    all_servers: Dict[str, ScopedMcpServerConfig] = {}
    all_errors: List[Dict[str, Any]] = []

    scopes = [
        ConfigScope.ENTERPRISE,
        ConfigScope.USER,
        ConfigScope.PROJECT,
        ConfigScope.LOCAL,
        ConfigScope.DYNAMIC,
    ]

    for scope in scopes:
        servers, errors = get_mcp_configs_by_scope(scope)
        all_errors.extend(errors)
        all_servers.update(servers)

    return all_servers, all_errors


def get_mcp_config_by_name(
    name: str,
) -> Optional[ScopedMcpServerConfig]:
    """Get an MCP server configuration by name."""
    servers, _ = get_all_mcp_configs()
    return servers.get(name)


def is_mcp_server_disabled(name: str) -> bool:
    """Check if an MCP server is disabled."""
    disabled_servers_str = os.environ.get("MCP_DISABLED_SERVERS", "")
    if disabled_servers_str:
        disabled_list = [s.strip() for s in disabled_servers_str.split(",")]
        if name in disabled_list:
            return True

    enabled_only_str = os.environ.get("MCP_ENABLED_ONLY_SERVERS", "")
    if enabled_only_str:
        enabled_list = [s.strip() for s in enabled_only_str.split(",")]
        return name not in enabled_list

    return False


def expand_env_vars(config: McpServerConfig) -> tuple[McpServerConfig, list[str]]:
    """
    Expand environment variables in an MCP server config.
    
    Returns tuple of (expanded_config, missing_vars).
    """
    import re
    
    missing_vars: list[str] = []
    
    def expand_string(s: str) -> tuple[str, list[str]]:
        var_pattern = re.compile(r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)')
        missing: list[str] = []
        
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2)
            value = os.environ.get(var_name)
            if value is None:
                missing.append(var_name)
                return match.group(0)
            return value
        
        expanded = var_pattern.sub(replace_var, s)
        return expanded, missing
    
    config_type = config.get("type") if isinstance(config, dict) else getattr(config, "type", None)
    
    if config_type is None or config_type == "stdio":
        command = config.get("command") if isinstance(config, dict) else getattr(config, "command", "")
        args = config.get("args", []) if isinstance(config, dict) else getattr(config, "args", [])
        env = config.get("env") if isinstance(config, dict) else getattr(config, "env", None)
        
        expanded_command, cmd_missing = expand_string(command)
        missing_vars.extend(cmd_missing)
        
        expanded_args = []
        for arg in args:
            exp_arg, arg_missing = expand_string(arg)
            expanded_args.append(exp_arg)
            missing_vars.extend(arg_missing)
        
        expanded_env = None
        if env:
            expanded_env = {}
            for k, v in env.items():
                exp_v, v_missing = expand_string(v)
                expanded_env[k] = exp_v
                missing_vars.extend(v_missing)
        
        return {
            "type": "stdio",
            "command": expanded_command,
            "args": expanded_args,
            "env": expanded_env,
        }, list(set(missing_vars))
    
    elif config_type in ("sse", "http", "ws"):
        url = config.get("url") if isinstance(config, dict) else getattr(config, "url", "")
        headers = config.get("headers") if isinstance(config, dict) else getattr(config, "headers", None)
        
        expanded_url, url_missing = expand_string(url)
        missing_vars.extend(url_missing)
        
        expanded_headers = None
        if headers:
            expanded_headers = {}
            for k, v in headers.items():
                exp_v, v_missing = expand_string(v)
                expanded_headers[k] = exp_v
                missing_vars.extend(v_missing)
        
        return {
            "type": config_type,
            "url": expanded_url,
            "headers": expanded_headers,
        }, list(set(missing_vars))
    
    else:
        return config, []


def is_mcp_server_denied(
    server_name: str,
    config: Optional[McpServerConfig] = None,
) -> bool:
    """
    Check if an MCP server is denied by enterprise policy.
    
    Checks name-based, command-based, and URL-based restrictions.
    """
    denied_servers_str = os.environ.get("DENIED_MCP_SERVERS", "")
    
    if denied_servers_str:
        denied_list = [s.strip() for s in denied_servers_str.split(",")]
        if server_name in denied_list:
            return True
    
    if config:
        command_array = get_server_command_array(config)
        if command_array:
            denied_commands_str = os.environ.get("DENIED_MCP_COMMANDS", "")
            if denied_commands_str:
                denied_commands = [s.strip() for s in denied_commands_str.split(";")]
                cmd_str = " ".join(command_array)
                for denied_cmd in denied_commands:
                    if denied_cmd in cmd_str:
                        return True
        
        server_url = get_server_url(config)
        if server_url:
            denied_urls_str = os.environ.get("DENIED_MCP_URLS", "")
            if denied_urls_str:
                denied_patterns = [s.strip() for s in denied_urls_str.split(";")]
                for pattern in denied_patterns:
                    if url_matches_pattern(server_url, pattern):
                        return True
    
    return False


def is_mcp_server_allowed_by_policy(
    server_name: str,
    config: Optional[McpServerConfig] = None,
) -> bool:
    """
    Check if an MCP server is allowed by enterprise policy.
    
    Checks name-based, command-based, and URL-based restrictions.
    """
    if is_mcp_server_denied(server_name, config):
        return False
    
    allowed_servers_str = os.environ.get("ALLOWED_MCP_SERVERS", "")
    
    if not allowed_servers_str:
        return True
    
    allowed_list = [s.strip() for s in allowed_servers_str.split(",")]
    
    if server_name in allowed_list:
        return True
    
    if config:
        command_array = get_server_command_array(config)
        if command_array:
            allowed_commands_str = os.environ.get("ALLOWED_MCP_COMMANDS", "")
            if allowed_commands_str:
                allowed_commands = [s.strip() for s in allowed_commands_str.split(";")]
                cmd_str = " ".join(command_array)
                for allowed_cmd in allowed_commands:
                    if allowed_cmd in cmd_str:
                        return True
        
        server_url = get_server_url(config)
        if server_url:
            allowed_urls_str = os.environ.get("ALLOWED_MCP_URLS", "")
            if allowed_urls_str:
                allowed_patterns = [s.strip() for s in allowed_urls_str.split(";")]
                for pattern in allowed_patterns:
                    if url_matches_pattern(server_url, pattern):
                        return True
    
    return False


def filter_mcp_servers_by_policy(
    configs: dict[str, McpServerConfig],
) -> tuple[dict[str, McpServerConfig], list[str]]:
    """
    Filter MCP server configs by managed policy (allowed/denied).
    
    Returns tuple of (allowed, blocked).
    """
    allowed: dict[str, McpServerConfig] = {}
    blocked: list[str] = []
    
    for name, config in configs.items():
        if config.get("type") == "sdk" or is_mcp_server_allowed_by_policy(name, config):
            allowed[name] = config
        else:
            blocked.append(name)
    
    return allowed, blocked


def add_mcp_config(
    name: str,
    config: McpServerConfig,
    scope: ConfigScope,
) -> None:
    """
    Add a new MCP server configuration.
    
    Args:
        name: The name of the server
        config: The server configuration
        scope: The configuration scope (LOCAL, USER, PROJECT)
    
    Raises:
        ValueError: If name is invalid or server already exists
    """
    import re
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError(
            f"Invalid name '{name}'. Names can only contain letters, numbers, hyphens, and underscores."
        )
    
    if scope not in (ConfigScope.LOCAL, ConfigScope.USER, ConfigScope.PROJECT):
        raise ValueError(f"Cannot add MCP server to scope: {scope}")
    
    existing = get_mcp_config_by_name(name)
    if existing:
        raise ValueError(f"MCP server '{name}' already exists")
    
    config_to_save: dict[str, Any] = dict(config) if isinstance(config, dict) else {}
    
    if scope == ConfigScope.LOCAL:
        local_path = get_project_mcp_file_path()
        existing_config: dict[str, Any] = {}
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    import json
                    existing_config = json.loads(content)
        
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}
        existing_config["mcpServers"][name] = config_to_save
        
        with open(local_path, "w", encoding="utf-8") as f:
            import json
            json.dump(existing_config, f, indent=2)
    
    elif scope == ConfigScope.USER:
        global_path = get_global_mcp_file_path()
        os.makedirs(os.path.dirname(global_path), exist_ok=True)
        existing_config = {}
        if os.path.exists(global_path):
            with open(global_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    import json
                    existing_config = json.loads(content)
        
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}
        existing_config["mcpServers"][name] = config_to_save
        
        with open(global_path, "w", encoding="utf-8") as f:
            import json
            json.dump(existing_config, f, indent=2)
    
    elif scope == ConfigScope.PROJECT:
        project_path = get_project_mcp_file_path()
        existing_config = {}
        if os.path.exists(project_path):
            with open(project_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    import json
                    existing_config = json.loads(content)
        
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}
        existing_config["mcpServers"][name] = config_to_save
        
        with open(project_path, "w", encoding="utf-8") as f:
            import json
            json.dump(existing_config, f, indent=2)


def remove_mcp_config(
    name: str,
    scope: ConfigScope,
) -> None:
    """
    Remove an MCP server configuration.
    
    Args:
        name: The name of the server to remove
        scope: The configuration scope
    
    Raises:
        ValueError: If server not found in specified scope
    """
    if scope not in (ConfigScope.LOCAL, ConfigScope.USER, ConfigScope.PROJECT):
        raise ValueError(f"Cannot remove MCP server from scope: {scope}")
    
    if scope == ConfigScope.LOCAL:
        local_path = get_project_mcp_file_path()
        if not os.path.exists(local_path):
            raise ValueError(f"No MCP server found with name '{name}' in local config")
        
        with open(local_path, "r", encoding="utf-8") as f:
            import json
            existing_config = json.loads(f.read())
        
        if "mcpServers" not in existing_config or name not in existing_config["mcpServers"]:
            raise ValueError(f"No MCP server found with name '{name}' in local config")
        
        del existing_config["mcpServers"][name]
        
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2)
    
    elif scope == ConfigScope.USER:
        global_path = get_global_mcp_file_path()
        if not os.path.exists(global_path):
            raise ValueError(f"No user-scoped MCP server found with name '{name}'")
        
        with open(global_path, "r", encoding="utf-8") as f:
            import json
            existing_config = json.loads(f.read())
        
        if "mcpServers" not in existing_config or name not in existing_config["mcpServers"]:
            raise ValueError(f"No user-scoped MCP server found with name '{name}'")
        
        del existing_config["mcpServers"][name]
        
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2)
    
    elif scope == ConfigScope.PROJECT:
        project_path = get_project_mcp_file_path()
        if not os.path.exists(project_path):
            raise ValueError(f"No MCP server found with name '{name}' in project config")
        
        with open(project_path, "r", encoding="utf-8") as f:
            import json
            existing_config = json.loads(f.read())
        
        if "mcpServers" not in existing_config or name not in existing_config["mcpServers"]:
            raise ValueError(f"No MCP server found with name '{name}' in project config")
        
        del existing_config["mcpServers"][name]
        
        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2)
