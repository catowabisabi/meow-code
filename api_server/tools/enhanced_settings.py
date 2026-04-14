"""Enhanced settings system - bridging gap with TypeScript settings/types.ts"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import json


class PermissionMode(Enum):
    DEFAULT = "default"
    ASK = "ask"
    BYPASS = "bypass"
    RESTRICTED = "restricted"


class SettingsSource(Enum):
    USER = "user"
    ENV = "env"
    MDM = "mdm"
    CLI = "cli"
    WORKSPACE = "workspace"
    DEFAULT = "default"


@dataclass
class PermissionRule:
    pattern: str
    tool: str
    behavior: str
    source: str = "user"


@dataclass
class HookConfig:
    if_clause: Optional[str] = None
    matcher: Optional[str] = None
    command: Optional[str] = None
    prompt: Optional[str] = None


@dataclass
class MarketplaceConfig:
    source: str
    install_location: Optional[str] = None


@dataclass
class SandboxSettings:
    disable_sandbox: bool = False
    allowed_paths: List[str] = field(default_factory=list)


@dataclass 
class Settings:
    """Main settings container - bridges TypeScript Settings interface."""
    
    permissions_allow: List[PermissionRule] = field(default_factory=list)
    permissions_deny: List[PermissionRule] = field(default_factory=list)
    permissions_ask: List[PermissionRule] = field(default_factory=list)
    permissions_default_mode: PermissionMode = PermissionMode.DEFAULT
    permissions_disable_bypass: bool = False
    permissions_additional_directories: List[str] = field(default_factory=list)
    
    hooks: List[HookConfig] = field(default_factory=list)
    
    marketplaces: List[MarketplaceConfig] = field(default_factory=list)
    
    sandbox: SandboxSettings = field(default_factory=SandboxSettings)
    
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    model: Optional[str] = None
    max_budget: Optional[float] = None
    
    agent_type: Optional[str] = None
    agent_tools: List[str] = field(default_factory=list)
    
    output_format: str = "text"
    verbose: bool = False
    debug: bool = False


class SettingsSourcePriority:
    """
    Manages settings from multiple sources with priority resolution.
    
    TypeScript equivalent: getSettingSourceDisplayNameLowercase() from settings.ts
    Python gap: No source priority/merge - flat key-value only.
    """
    
    SOURCE_ORDER = [
        SettingsSource.WORKSPACE,
        SettingsSource.MDM,
        SettingsSource.CLI,
        SettingsSource.USER,
        SettingsSource.ENV,
        SettingsSource.DEFAULT,
    ]
    
    @classmethod
    def resolve(cls, sources: Dict[SettingsSource, Any]) -> Any:
        """Resolve setting value based on source priority."""
        for source in cls.SOURCE_ORDER:
            if source in sources and sources[source] is not None:
                return sources[source]
        return None


class SettingsMerger:
    """
    Merges settings from multiple sources.
    
    TypeScript equivalent: mergeSettings() pattern
    """
    
    @classmethod
    def merge_permission_rules(
        cls, 
        *rule_lists: List[PermissionRule]
    ) -> Dict[str, List[PermissionRule]]:
        merged: Dict[str, List[PermissionRule]] = {}
        for rules in rule_lists:
            for rule in rules:
                key = rule.tool
                if key not in merged:
                    merged[key] = []
                merged[key].append(rule)
        return merged
    
    @classmethod
    def merge_settings(cls, *settings: Settings) -> Settings:
        result = Settings()
        
        for s in settings:
            if s.permissions_allow:
                result.permissions_allow.extend(s.permissions_allow)
            if s.permissions_deny:
                result.permissions_deny.extend(s.permissions_deny)
            if s.permissions_ask:
                result.permissions_ask.extend(s.permissions_ask)
            
            if s.hooks:
                result.hooks.extend(s.hooks)
            
            if s.marketplaces:
                result.marketplaces.extend(s.marketplaces)
            
            if s.env_vars:
                result.env_vars.update(s.env_vars)
            
            if s.model:
                result.model = s.model
            if s.max_budget:
                result.max_budget = s.max_budget
        
        return result


class SettingsValidator:
    """Validates settings against schemas."""
    
    @staticmethod
    def validate_permission_rule(rule: Dict[str, Any]) -> bool:
        required = ["pattern", "tool", "behavior"]
        return all(k in rule for k in required)
    
    @staticmethod
    def validate_hook_config(hook: Dict[str, Any]) -> bool:
        has_command = "command" in hook
        has_prompt = "prompt" in hook
        return has_command or has_prompt


class SettingsManager:
    """
    Central settings management with persistence.
    
    TypeScript equivalent: settings.ts exports
    Python gap: Only 6/80+ fields implemented.
    """
    
    def __init__(self):
        self._settings: Settings = Settings()
        self._sources: Dict[str, SettingsSource] = {}
        self._listeners: List[Callable[[str, Any], None]] = []
    
    def get(self, key: str) -> Any:
        return getattr(self._settings, key, None)
    
    def set(self, key: str, value: Any, source: SettingsSource = SettingsSource.USER) -> None:
        setattr(self._settings, key, value)
        self._sources[key] = source
        self._notify(key, value)
    
    def get_source(self, key: str) -> SettingsSource:
        return self._sources.get(key, SettingsSource.DEFAULT)
    
    def add_listener(self, listener: Callable[[str, Any], None]) -> None:
        self._listeners.append(listener)
    
    def _notify(self, key: str, value: Any) -> None:
        for listener in self._listeners:
            listener(key, value)
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """Load settings from dictionary."""
        if "permissions" in data:
            perms = data["permissions"]
            if "allow" in perms:
                self._settings.permissions_allow = [
                    PermissionRule(**r) for r in perms["allow"]
                ]
            if "deny" in perms:
                self._settings.permissions_deny = [
                    PermissionRule(**r) for r in perms["deny"]
                ]
            if "ask" in perms:
                self._settings.permissions_ask = [
                    PermissionRule(**r) for r in perms["ask"]
                ]
            if "defaultMode" in perms:
                self._settings.permissions_default_mode = PermissionMode(
                    perms["defaultMode"]
                )
            if "additionalDirectories" in perms:
                self._settings.permissions_additional_directories = perms["additionalDirectories"]
        
        if "hooks" in data:
            self._settings.hooks = [HookConfig(**h) for h in data["hooks"]]
        
        if "env" in data:
            self._settings.env_vars = data["env"]
        
        if "sandbox" in data:
            self._settings.sandbox = SandboxSettings(**data["sandbox"])
        
        if "model" in data:
            self._settings.model = data["model"]
        
        if "maxBudget" in data:
            self._settings.max_budget = data["maxBudget"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export settings to dictionary."""
        return {
            "permissions": {
                "allow": [
                    {"pattern": r.pattern, "tool": r.tool, "behavior": r.behavior}
                    for r in self._settings.permissions_allow
                ],
                "deny": [
                    {"pattern": r.pattern, "tool": r.tool, "behavior": r.behavior}
                    for r in self._settings.permissions_deny
                ],
                "ask": [
                    {"pattern": r.pattern, "tool": r.tool, "behavior": r.behavior}
                    for r in self._settings.permissions_ask
                ],
                "defaultMode": self._settings.permissions_default_mode.value,
                "additionalDirectories": self._settings.permissions_additional_directories,
            },
            "hooks": [
                {"if": h.if_clause, "matcher": h.matcher, "command": h.command, "prompt": h.prompt}
                for h in self._settings.hooks
            ],
            "env": self._settings.env_vars,
            "sandbox": {
                "disableSandbox": self._settings.sandbox.disable_sandbox,
                "allowedPaths": self._settings.sandbox.allowed_paths,
            },
            "model": self._settings.model,
            "maxBudget": self._settings.max_budget,
        }


_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
