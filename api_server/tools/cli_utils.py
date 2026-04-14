"""CLI utilities - bridging gap with TypeScript cli/"""
import asyncio
import logging
import sys
import signal
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ExitCode(Enum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2
    EXECUTION_ERROR = 3
    PERMISSION_DENIED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    NETWORK_ERROR = 7
    AUTH_ERROR = 8
    CONFIG_ERROR = 9


class GracefulShutdown:
    """
    Graceful shutdown handler.
    
    TypeScript equivalent: cli/exit.ts
    Python gap: No graceful shutdown handler.
    """
    
    def __init__(self):
        self._shutdown_callbacks: List[Callable] = []
        self._force_shutdown_callbacks: List[Callable] = []
        self._is_shutting_down = False
        self._exit_code = ExitCode.SUCCESS
    
    def register_shutdown_callback(self, callback: Callable) -> None:
        self._shutdown_callbacks.append(callback)
    
    def register_force_shutdown_callback(self, callback: Callable) -> None:
        self._force_shutdown_callbacks.append(callback)
    
    async def shutdown(self, exit_code: ExitCode = ExitCode.SUCCESS) -> None:
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._exit_code = exit_code
        
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Shutdown callback error: {e}")
        
        await asyncio.sleep(0.1)
        
        sys.exit(exit_code.value)
    
    def force_shutdown(self) -> None:
        for callback in self._force_shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Force shutdown callback error: {e}")
        
        sys.exit(ExitCode.GENERAL_ERROR.value)


_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdown()
    return _shutdown_handler


class FeatureFlags:
    """
    Feature flag infrastructure.
    
    TypeScript equivalent: cli/print.ts with feature flag support
    Python gap: No feature flag infrastructure.
    """
    
    def __init__(self):
        self._flags: Dict[str, bool] = {}
        self._overrides: Dict[str, Optional[bool]] = {}
        self._cache: Dict[str, bool] = {}
    
    def register_flag(self, name: str, default_value: bool = False) -> None:
        self._flags[name] = default_value
    
    def is_enabled(self, name: str) -> bool:
        if name in self._overrides and self._overrides[name] is not None:
            return self._overrides[name]
        
        if name in self._cache:
            return self._cache[name]
        
        value = self._flags.get(name, False)
        
        env_var = f"CLAUDE_{name.upper().replace('-', '_')}"
        if env_var in os.environ:
            value = os.environ[env_var].lower() in ("true", "1", "yes", "on")
        
        self._cache[name] = value
        return value
    
    def override(self, name: str, value: Optional[bool]) -> None:
        self._overrides[name] = value
        self._cache[name] = value if value is not None else self._flags.get(name, False)
    
    def get(self, name: str, default: bool = False) -> bool:
        return self.is_enabled(name) if name in self._flags else default


_feature_flags: Optional[FeatureFlags] = None


def get_feature_flags() -> FeatureFlags:
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags


def is_env_truthy(env_var: str) -> bool:
    return os.getenv(env_var, "").lower() in ("true", "1", "yes", "on", "enabled")


import os
