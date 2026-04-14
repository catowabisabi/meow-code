"""Bash shell provider with RC file sourcing - bridging gap with TypeScript shell/bashProvider.ts"""
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class BashExecResult:
    stdout: str
    stderr: str
    exit_code: int


class BashRCContext:
    def __init__(self):
        self.env_vars: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}
        self.functions: Dict[str, str] = {}
        self.path_added: List[str] = []
    
    def apply(self, env: Dict[str, str]) -> Dict[str, str]:
        result = dict(env)
        result.update(self.env_vars)
        
        for key, value in self.env_vars.items():
            result[key] = value
        
        return result


class BashRCLoader:
    def __init__(self):
        self._cache: Optional[BashRCContext] = None
        self._bashrc_paths = [
            "~/.bashrc",
            "~/.bash_profile",
            "~/.profile",
        ]
    
    async def load(self, shell_path: str = "/bin/bash") -> BashRCContext:
        if self._cache:
            return self._cache
        
        context = BashRCContext()
        
        bashrc_content = await self._find_bashrc()
        if bashrc_content:
            await self._parse_bashrc(bashrc_content, context)
        
        self._cache = context
        return context
    
    async def _find_bashrc(self) -> Optional[str]:
        home = os.path.expanduser("~")
        
        for bashrc_path in self._bashrc_paths:
            expanded = os.path.expanduser(bashrc_path)
            if os.path.exists(expanded):
                try:
                    with open(expanded, 'r', encoding='utf-8') as f:
                        return f.read()
                except OSError:
                    pass
        
        return None
    
    async def _parse_bashrc(self, content: str, context: BashRCContext) -> None:
        for line in content.split('\n'):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('export '):
                if '=' in line:
                    var_part = line[7:].strip()
                    if var_part.startswith('{'):
                        continue
                    if '=' in var_part:
                        key, value = var_part.split('=', 1)
                        value = value.strip('"\'')
                        context.env_vars[key] = value
            
            elif line.startswith('alias '):
                alias_def = line[7:].strip()
                if '=' in alias_def:
                    name, value = alias_def.split('=', 1)
                    name = name.strip()
                    value = value.strip('"\'')
                    context.aliases[name] = value
            
            elif 'PATH=' in line and 'export' in line:
                if line.startswith('export '):
                    var_part = line[7:].strip()
                    if 'PATH=' in var_part:
                        path_val = var_part.split('PATH=', 1)[1].split()[0].strip('"\'')
                        context.env_vars['PATH'] = path_val


class BashProvider:
    def __init__(self, shell_path: str = "/bin/bash"):
        self.shell_path = shell_path
        self.shell_type = "bash"
        self.rc_loader = BashRCLoader()
        self.rc_context: Optional[BashRCContext] = None
    
    async def initialize(self) -> None:
        self.rc_context = await self.rc_loader.load(self.shell_path)
    
    def get_spawn_args(self, command: str) -> List[str]:
        return ["-c", command]
    
    def get_environment_overrides(self, command: str) -> Dict[str, str]:
        if self.rc_context:
            return self.rc_context.env_vars
        return {}
    
    async def execute_rc_sourced_command(
        self,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> BashExecResult:
        if not self.rc_context:
            await self.initialize()
        
        if env is None:
            env = dict(os.environ)
        
        env = self.rc_context.apply(env)
        
        proc = await asyncio.create_subprocess_exec(
            self.shell_path,
            "-c",
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            return BashExecResult(
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                exit_code=proc.returncode or 0
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return BashExecResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=-1
            )
    
    def supports_rc_sourcing(self) -> bool:
        return True


_bash_provider_cache: Optional[BashProvider] = None


def get_bash_provider() -> BashProvider:
    global _bash_provider_cache
    if _bash_provider_cache is None:
        shell = os.getenv("CLAUDE_CODE_SHELL", "/bin/bash")
        _bash_provider_cache = BashProvider(shell_path=shell)
    return _bash_provider_cache


def reset_bash_provider() -> None:
    global _bash_provider_cache
    _bash_provider_cache = None
