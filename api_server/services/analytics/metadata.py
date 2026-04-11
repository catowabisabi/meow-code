"""
Shared event metadata enrichment for analytics systems.

This module provides:
- Core event metadata collection
- Environment context building
- User identification
"""

import os
import platform
import time
import uuid
import hashlib
from typing import Any, Optional


_device_id: Optional[str] = None
_session_id: Optional[str] = None
_main_loop_model: Optional[str] = None


def _get_or_create_device_id() -> str:
    global _device_id
    if _device_id is not None:
        return _device_id

    config_dir = os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    device_id_file = os.path.join(config_dir, ".device_id")

    try:
        if os.path.exists(device_id_file):
            with open(device_id_file, "r") as f:
                _device_id = f.read().strip()
    except Exception:
        pass

    if _device_id is None:
        _device_id = uuid.uuid4().hex
        try:
            os.makedirs(os.path.dirname(device_id_file), exist_ok=True)
            with open(device_id_file, "w") as f:
                f.write(_device_id)
        except Exception:
            pass

    return _device_id


def get_or_create_user_id() -> str:
    return _get_or_create_device_id()


def get_session_id() -> str:
    global _session_id
    if _session_id is not None:
        return _session_id

    _session_id = os.getenv("CLAUDE_CODE_SESSION_ID") or uuid.uuid4().hex
    return _session_id


def get_main_loop_model() -> str:
    global _main_loop_model
    if _main_loop_model is not None:
        return _main_loop_model

    model = os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-20250514"
    _main_loop_model = model
    return _main_loop_model


def set_main_loop_model(model: str) -> None:
    global _main_loop_model
    _main_loop_model = model


def get_is_interactive() -> bool:
    return os.getenv("CLAUDE_CODE_INTERACTIVE", "true").lower() != "false"


def get_client_type() -> str:
    return os.getenv("CLAUDE_CODE_CLIENT_TYPE", "unknown")


def _get_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        if "microsoft" in platform.release().lower():
            return "wsl"
        return "linux"
    return system


def _get_arch() -> str:
    return platform.machine().lower()


def _get_node_version() -> str:
    return platform.python_version()


def _get_terminal() -> Optional[str]:
    return os.getenv("TERM") or os.getenv("TERMINAL")


def _get_package_managers() -> list[str]:
    managers = []
    for name in ["npm", "yarn", "pnpm", "bun"]:
        if os.system(f"{name} --version > /dev/null 2>&1") == 0:
            managers.append(name)
    return managers


def _get_runtimes() -> list[str]:
    runtimes = []
    for name in ["node", "python", "ruby", "go"]:
        if os.system(f"{name} --version > /dev/null 2>&1") == 0:
            runtimes.append(name)
    return runtimes


def _is_running_with_bun() -> bool:
    return os.getenv("BUN_ENV") is not None or "bun" in os.getenv("_", "").lower()


def _is_ci() -> bool:
    return os.getenv("CI") is not None


def _is_claubbit() -> bool:
    return os.getenv("CLAUBBIT") is not None


def _is_claude_code_remote() -> bool:
    return os.getenv("CLAUDE_CODE_REMOTE") is not None


def _is_local_agent_mode() -> bool:
    return os.getenv("CLAUDE_CODE_ENTRYPOINT") == "local-agent"


def _is_conductor() -> bool:
    return os.getenv("CLAUDE_CODE_CONDUCTOR") is not None


def _is_github_action() -> bool:
    return os.getenv("GITHUB_ACTIONS") is not None


def _is_claude_code_action() -> bool:
    return os.getenv("CLAUDE_CODE_ACTION") is not None


def _is_claude_ai_auth() -> bool:
    return os.getenv("CLAUDE_AI_AUTH") is not None


def _get_deployment_environment() -> str:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    if "staging" in base_url:
        return "staging"
    if "dev" in base_url:
        return "development"
    return "production"


def _get_version() -> str:
    return os.getenv("CLAUDE_CODE_VERSION", "unknown")


def _get_build_time() -> str:
    return os.getenv("CLAUDE_CODE_BUILD_TIME", "")


def _get_wsl_version() -> Optional[str]:
    if _get_platform() != "wsl":
        return None
    try:
        with open("/proc/version", "r") as f:
            content = f.read().lower()
            if "microsoft" in content:
                return "2"
    except Exception:
        pass
    return None


def _get_repo_remote_hash() -> Optional[str]:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "ls-remote", "--get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            if remote_url:
                hash_val = hashlib.sha256(remote_url.encode()).hexdigest()
                return hash_val[:16]
    except Exception:
        pass
    return None


def _detect_vcs() -> list[str]:
    vcs = []
    if os.path.exists(".git"):
        vcs.append("git")
    if os.path.exists(".hg"):
        vcs.append("hg")
    return vcs


def _build_env_context() -> dict[str, Any]:
    package_managers = _get_package_managers()
    runtimes = _get_runtimes()
    vcs = _detect_vcs()
    wsl_version = _get_wsl_version()

    return {
        "platform": _get_platform(),
        "platformRaw": os.getenv("CLAUDE_CODE_HOST_PLATFORM") or platform.system().lower(),
        "arch": _get_arch(),
        "nodeVersion": _get_node_version(),
        "terminal": _get_terminal(),
        "packageManagers": ",".join(package_managers),
        "runtimes": ",".join(runtimes),
        "isRunningWithBun": _is_running_with_bun(),
        "isCi": _is_ci(),
        "isClaubbit": _is_claubbit(),
        "isClaudeCodeRemote": _is_claude_code_remote(),
        "isLocalAgentMode": _is_local_agent_mode(),
        "isConductor": _is_conductor(),
        "isGithubAction": _is_github_action(),
        "isClaudeCodeAction": _is_claude_code_action(),
        "isClaudeAiAuth": _is_claude_ai_auth(),
        "version": _get_version(),
        "buildTime": _get_build_time(),
        "deploymentEnvironment": _get_deployment_environment(),
        **({
            "remoteEnvironmentType": os.getenv("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE")
        } if os.getenv("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") else {}),
        **({
            "coworkerType": os.getenv("CLAUDE_CODE_COWORKER_TYPE")
        } if os.getenv("CLAUDE_CODE_COWORKER_TYPE") else {}),
        **({
            "claudeCodeContainerId": os.getenv("CLAUDE_CODE_CONTAINER_ID")
        } if os.getenv("CLAUDE_CODE_CONTAINER_ID") else {}),
        **({
            "claudeCodeRemoteSessionId": os.getenv("CLAUDE_CODE_REMOTE_SESSION_ID")
        } if os.getenv("CLAUDE_CODE_REMOTE_SESSION_ID") else {}),
        **({
            "tags": os.getenv("CLAUDE_CODE_TAGS")
        } if os.getenv("CLAUDE_CODE_TAGS") else {}),
        **({
            "githubEventName": os.getenv("GITHUB_EVENT_NAME")
        } if os.getenv("GITHUB_EVENT_NAME") else {}),
        **({
            "githubActionsRunnerEnvironment": os.getenv("RUNNER_ENVIRONMENT")
        } if os.getenv("RUNNER_ENVIRONMENT") else {}),
        **({
            "githubActionsRunnerOs": os.getenv("RUNNER_OS")
        } if os.getenv("RUNNER_OS") else {}),
        **({
            "wslVersion": wsl_version
        } if wsl_version else {}),
        "vcs": ",".join(vcs) if vcs else None,
    }


def _build_process_metrics() -> Optional[dict[str, Any]]:
    try:
        import psutil

        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        process = psutil.Process()

        return {
            "uptime": time.time() - psutil.boot_time(),
            "rss": process.memory_info().rss,
            "heapTotal": process.memory_info().rss,
            "heapUsed": process.memory_info().rss,
            "external": 0,
            "arrayBuffers": 0,
            "constrainedMemory": mem.available,
            "cpuUsage": {"user": 0, "system": 0},
            "cpuPercent": cpu,
        }
    except Exception:
        return {
            "uptime": time.time(),
            "rss": 0,
            "heapTotal": 0,
            "heapUsed": 0,
            "external": 0,
            "arrayBuffers": 0,
            "constrainedMemory": None,
            "cpuUsage": {"user": 0, "system": 0},
            "cpuPercent": None,
        }


async def get_event_metadata(
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    options = options or {}

    model = options.get("model") or get_main_loop_model()
    betas = options.get("betas") or ""

    env_context = _build_env_context()
    process_metrics = _build_process_metrics()
    repo_remote_hash = _get_repo_remote_hash()

    metadata: dict[str, Any] = {
        "model": model,
        "sessionId": get_session_id(),
        "userType": os.getenv("USER_TYPE") or "",
        "envContext": env_context,
        "isInteractive": str(get_is_interactive()),
        "clientType": get_client_type(),
        **({
            "betas": betas
        } if betas else {}),
        **({
            "processMetrics": process_metrics
        } if process_metrics else {}),
        "sweBenchRunId": os.getenv("SWE_BENCH_RUN_ID") or "",
        "sweBenchInstanceId": os.getenv("SWE_BENCH_INSTANCE_ID") or "",
        "sweBenchTaskId": os.getenv("SWE_BENCH_TASK_ID") or "",
        **({
            "entrypoint": os.getenv("CLAUDE_CODE_ENTRYPOINT")
        } if os.getenv("CLAUDE_CODE_ENTRYPOINT") else {}),
        **({
            "agentSdkVersion": os.getenv("CLAUDE_AGENT_SDK_VERSION")
        } if os.getenv("CLAUDE_AGENT_SDK_VERSION") else {}),
        **({
            "device_id": _get_or_create_device_id()
        } if True else {}),
        **({
            "rh": repo_remote_hash
        } if repo_remote_hash else {}),
    }

    return metadata