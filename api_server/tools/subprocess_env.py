"""Secure subprocess environment - bridging gap with TypeScript subprocessEnv.ts"""
import os
import logging
from typing import Dict, Optional, Set, List


logger = logging.getLogger(__name__)


SECRET_ENV_VARS: Set[str] = {
    "API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID",
    "GITHUB_TOKEN", "GH_TOKEN",
    "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY",
    "DATABASE_URL", "DB_PASSWORD", "DB_HOST", "DB_USER", "DB_PASS",
    "REDIS_URL", "REDIS_PASSWORD",
    "SENDGRID_API_KEY", "MAILGUN_API_KEY",
    "JWT_SECRET", "SESSION_SECRET", "CSRF_SECRET",
    "PRIVATE_KEY", "SSH_PRIVATE_KEY", "GPG_KEY",
    "CLOUDFLARE_API_KEY", "CF_API_KEY",
    "VULTR_API_KEY", "DIGITALOCEAN_TOKEN",
    "HEROKU_API_KEY", "RAILWAY_TOKEN",
    "NETLIFY_API_KEY", "VERCEL_TOKEN",
    "NPM_TOKEN", "YARN_TOKEN", "PYPI_TOKEN",
    "DOCKER_USERNAME", "DOCKER_PASSWORD",
    "S3_SECRET", "S3_ACCESS_KEY",
    "AZURE_STORAGE_KEY", "AZURE_CLIENT_SECRET",
}

ALLOWED_ENV_VARS: Set[str] = {
    "PATH", "HOME", "USER", "SHELL", "PWD", "OLDPWD",
    "LANG", "LC_ALL", "LANGUAGE", "TERM", "TERMINAL",
    "EDITOR", "VISUAL", "PAGER",
    "CLICOLOR", "CLICOLOR_FORCE", "NO_COLOR",
    "DEBUG", "VERBOSE", "LOG_LEVEL",
    "TMPDIR", "TEMP", "TMP",
    "CI", "CONTINUOUS_INTEGRATION",
    "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL",
    "AGENT_ID", "SESSION_ID", "RUN_ID",
    "CLAUDE_CODE_SHELL", "CLAUDE_API_KEY", "ANTHROPIC_BASE_URL",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
    "MCP_SERVERS", "MCP_TOOL_ROOTS",
    "DOTNET_CLI_TELEMETRY_OPTOUT", "DOTNET_CLI_HOME",
    "CARGO_HOME", "RUSTUP_HOME",
    "npm_config_cache", "yarn_cache_folder",
    "GIT_EDITOR", "GIT_SSH", "GIT_SSH_COMMAND",
    "HGFS_PROXY", "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE",
}

MINIMAL_ENV_VARS: Set[str] = {
    "HOME", "PATH", "USER", "SHELL", "PWD", "TERM",
}


class SubprocessEnvFilter:
    def __init__(self):
        self.debug_mode = os.getenv("CLAUDE_DEBUG", "false").lower() in ("true", "1", "yes")
    
    def filter_env(self, env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        if env is None:
            env = dict(os.environ)
        
        if self.debug_mode:
            return env
        
        filtered: Dict[str, str] = {}
        
        for key, value in env.items():
            if key in MINIMAL_ENV_VARS:
                filtered[key] = value
            elif key in ALLOWED_ENV_VARS:
                filtered[key] = value
            elif key.startswith(("CLAUDE_", "CLAUDECODE_")):
                filtered[key] = value
            elif key.startswith("MCP_"):
                filtered[key] = value
            elif key.startswith("npm_config_"):
                filtered[key] = value
            elif key.startswith("yarn_"):
                filtered[key] = value
            elif key.startswith("GIT_"):
                filtered[key] = value
            elif key in SECRET_ENV_VARS:
                filtered[key] = self._mask_secret(value)
            elif "SECRET" in key or "PASSWORD" in key or "TOKEN" in key or "KEY" in key:
                filtered[key] = self._mask_secret(value)
            elif key.endswith("_URL") or key.endswith("_URI"):
                if "secret" in key.lower() or "token" in key.lower():
                    filtered[key] = self._mask_secret(value)
                else:
                    filtered[key] = value
            else:
                filtered[key] = value
        
        return filtered
    
    def _mask_secret(self, value: str, show_chars: int = 4) -> str:
        if len(value) <= show_chars * 2:
            return "***"
        return value[:show_chars] + "***" + value[-show_chars:]


_filter = SubprocessEnvFilter()


def get_subprocess_env(include_debug: bool = False) -> Dict[str, str]:
    env = _filter.filter_env()
    env["CLAUDECODE"] = "1"
    return env


def get_filtered_env(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    return _filter.filter_env(env)


class EnvVarValidator:
    @staticmethod
    def is_safe_to_pass(key: str) -> bool:
        if key in MINIMAL_ENV_VARS or key in ALLOWED_ENV_VARS:
            return True
        if key.startswith(("CLAUDE_", "CLAUDECODE_", "MCP_")):
            return True
        if key in SECRET_ENV_VARS:
            return False
        if "SECRET" in key or "PASSWORD" in key or "TOKEN" in key:
            return False
        return True
    
    @staticmethod
    def get_secret_vars(env: Dict[str, str]) -> List[str]:
        secrets = []
        for key in env:
            if key in SECRET_ENV_VARS:
                secrets.append(key)
            elif "SECRET" in key or "PASSWORD" in key or "TOKEN" in key:
                secrets.append(key)
        return secrets
