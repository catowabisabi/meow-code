"""Model selection and routing - bridging gap with TypeScript utils/model/"""
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import os


class Model(Enum):
    CLAUDE_OPUS = "opus"
    CLAUDE_SONNET = "sonnet"
    CLAUDE_HAIKU = "haiku"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    UNKNOWN = "unknown"


class ModelProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    AWS = "aws"
    AZURE = "azure"
    LOCAL = "local"


@dataclass
class ModelInfo:
    name: str
    provider: ModelProvider
    api_key_env: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True


MODEL_REGISTRY: Dict[str, ModelInfo] = {
    "opus": ModelInfo(
        name="claude-opus-4-20240920",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=False,
    ),
    "sonnet": ModelInfo(
        name="claude-sonnet-4-20240920",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=False,
    ),
    "haiku": ModelInfo(
        name="claude-haiku-4-20240920",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=False,
    ),
    "claude-3-5-sonnet": ModelInfo(
        name="claude-3-5-sonnet-20241022",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=8192,
        supports_vision=True,
    ),
    "claude-3-opus": ModelInfo(
        name="claude-3-opus-20240229",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=True,
    ),
    "claude-3-sonnet": ModelInfo(
        name="claude-3-sonnet-20240229",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=True,
    ),
    "claude-3-haiku": ModelInfo(
        name="claude-3-haiku-20240307",
        provider=ModelProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        supports_vision=True,
    ),
    "gpt-4": ModelInfo(
        name="gpt-4",
        provider=ModelProvider.OPENAI,
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        supports_vision=False,
    ),
    "gpt-4-turbo": ModelInfo(
        name="gpt-4-turbo",
        provider=ModelProvider.OPENAI,
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        supports_vision=True,
    ),
    "gpt-3.5-turbo": ModelInfo(
        name="gpt-3.5-turbo",
        provider=ModelProvider.OPENAI,
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        supports_vision=False,
    ),
}


def get_model_info(model_name: str) -> Optional[ModelInfo]:
    normalized = model_name.lower().replace(" ", "-")
    
    if normalized in MODEL_REGISTRY:
        return MODEL_REGISTRY[normalized]
    
    for key, info in MODEL_REGISTRY.items():
        if key in normalized or normalized in key:
            return info
    
    return None


def get_api_key_for_model(model_name: str) -> Optional[str]:
    info = get_model_info(model_name)
    if info and info.api_key_env:
        return os.getenv(info.api_key_env)
    return None


def get_base_url_for_model(model_name: str) -> Optional[str]:
    info = get_model_info(model_name)
    if info:
        if info.base_url:
            return info.base_url
        
        if info.provider == ModelProvider.ANTHROPIC:
            return os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        elif info.provider == ModelProvider.OPENAI:
            return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        elif info.provider == ModelProvider.GOOGLE:
            return os.getenv("GOOGLE_BASE_URL", "https://api.google.com")
    
    return None


def get_max_tokens_for_model(model_name: str) -> int:
    info = get_model_info(model_name)
    if info:
        return info.max_tokens
    return 4096


def supports_vision(model_name: str) -> bool:
    info = get_model_info(model_name)
    if info:
        return info.supports_vision
    return False


def supports_tools(model_name: str) -> bool:
    info = get_model_info(model_name)
    if info:
        return info.supports_tools
    return True


def route_to_api_endpoint(model_name: str, endpoint: str = "/v1/messages") -> str:
    base_url = get_base_url_for_model(model_name)
    if base_url:
        return f"{base_url.rstrip('/')}{endpoint}"
    
    return f"https://api.anthropic.com{endpoint}"


def parse_model_string(model: str) -> tuple[str, Optional[str], Optional[str]]:
    parts = model.split("@")
    model_name = parts[0]
    provider = None
    region = None
    
    if len(parts) > 1:
        provider = parts[1]
    if len(parts) > 2:
        region = parts[2]
    
    return model_name, provider, region


class ModelSelector:
    def __init__(self, default_model: str = "sonnet"):
        self.default_model = default_model
        self.model_overrides: Dict[str, str] = {}
    
    def select_model(
        self,
        task_type: str,
        complexity: str = "medium",
        user_preference: Optional[str] = None
    ) -> str:
        if user_preference:
            return user_preference
        
        if task_type == "coding":
            if complexity == "high":
                return "opus"
            return "sonnet"
        elif task_type == "analysis":
            return "opus"
        elif task_type == "quick":
            return "haiku"
        elif task_type == "creative":
            return "sonnet"
        else:
            return self.default_model
    
    def set_override(self, task_type: str, model: str) -> None:
        self.model_overrides[task_type] = model
    
    def get_override(self, task_type: str) -> Optional[str]:
        return self.model_overrides.get(task_type)


_model_selector: Optional[ModelSelector] = None


def get_model_selector() -> ModelSelector:
    global _model_selector
    if _model_selector is None:
        default = os.getenv("CLAUDE_MODEL", "sonnet")
        _model_selector = ModelSelector(default_model=default)
    return _model_selector
