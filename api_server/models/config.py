"""Configuration models for provider and model management."""
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ProviderConfig:
    id: str
    name: str
    api_base_url: Optional[str]
    api_key: Optional[str]
    models: List[str] = field(default_factory=list)
    enabled: bool = True

    def model_dump(self, **kwargs) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "apiBaseUrl": self.api_base_url,
            "apiKey": self.api_key,
            "models": self.models,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        return cls(
            id=data.get("id", data.get("type", "")),
            name=data.get("name", data.get("displayName", "")),
            api_base_url=data.get("apiBaseUrl", data.get("api_base_url")),
            api_key=data.get("apiKey", data.get("api_key", "")),
            models=data.get("models", []),
            enabled=data.get("enabled", True)
        )


@dataclass
class ProviderCapabilities:
    tool_calling: bool = False
    streaming: bool = False
    thinking: bool = False
    vision: bool = False

    def model_dump(self, **kwargs) -> dict:
        return {
            "toolCalling": self.tool_calling,
            "streaming": self.streaming,
            "thinking": self.thinking,
            "vision": self.vision
        }


@dataclass
class KnownProvider:
    id: str
    display_name: str
    default_base_url: str
    capabilities: ProviderCapabilities

    def model_dump(self, **kwargs) -> dict:
        return {
            "id": self.id,
            "displayName": self.display_name,
            "defaultBaseUrl": self.default_base_url,
            "capabilities": self.capabilities.model_dump()
        }


KNOWN_PROVIDERS: Dict[str, KnownProvider] = {
    "anthropic": KnownProvider(
        id="anthropic",
        display_name="Anthropic (Claude)",
        default_base_url="https://api.anthropic.com",
        capabilities=ProviderCapabilities(tool_calling=True, streaming=True, thinking=True, vision=True)
    ),
    "deepseek": KnownProvider(
        id="deepseek",
        display_name="DeepSeek",
        default_base_url="https://api.deepseek.com/v1",
        capabilities=ProviderCapabilities(tool_calling=True, streaming=True, thinking=False, vision=False)
    ),
    "minimax": KnownProvider(
        id="minimax",
        display_name="MiniMax",
        default_base_url="https://api.minimax.io/v1",
        capabilities=ProviderCapabilities(tool_calling=True, streaming=True, thinking=False, vision=False)
    ),
    "openai": KnownProvider(
        id="openai",
        display_name="OpenAI",
        default_base_url="https://api.openai.com/v1",
        capabilities=ProviderCapabilities(tool_calling=True, streaming=True, thinking=False, vision=True)
    ),
    "ollama": KnownProvider(
        id="ollama",
        display_name="Ollama (Local)",
        default_base_url="http://localhost:11434/v1",
        capabilities=ProviderCapabilities(tool_calling=False, streaming=True, thinking=False, vision=False)
    ),
    "openai-compatible": KnownProvider(
        id="openai-compatible",
        display_name="OpenAI Compatible",
        default_base_url="",
        capabilities=ProviderCapabilities(tool_calling=True, streaming=True, thinking=False, vision=False)
    ),
}


@dataclass
class HotkeyEntry:
    key: str
    model: str
    provider: str

    def model_dump(self, **kwargs) -> dict:
        return {"key": self.key, "model": self.model, "provider": self.provider}

    @classmethod
    def from_dict(cls, data: dict) -> "HotkeyEntry":
        return cls(key=data.get("key", ""), model=data.get("model", ""), provider=data.get("provider", ""))


@dataclass
class ModelsConfig:
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    default_provider: Optional[str] = None
    default_model: Optional[str] = None

    def model_dump(self, **kwargs) -> dict:
        return {
            "providers": {k: v.model_dump() for k, v in self.providers.items()},
            "defaultProvider": self.default_provider,
            "defaultModel": self.default_model
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelsConfig":
        providers = {}
        for pid, pdata in data.get("providers", {}).items():
            if isinstance(pdata, dict):
                providers[pid] = ProviderConfig.from_dict({**pdata, "id": pid})
            else:
                providers[pid] = pdata
        
        return cls(
            providers=providers,
            default_provider=data.get("defaultProvider", data.get("default_provider")),
            default_model=data.get("defaultModel", data.get("default_model"))
        )
