"""Message models for unified multi-model adapter."""
from dataclasses import dataclass, field
from typing import Union, List, Optional

from .content_block import ContentBlock, content_block_from_dict


@dataclass
class Message:
    role: str
    content: Union[str, List[ContentBlock]]

    def model_dump(self, **kwargs) -> dict:
        if isinstance(self.content, list):
            return {"role": self.role, "content": [block.model_dump() if hasattr(block, 'model_dump') else block for block in self.content]}
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        content = data.get("content", "")
        if isinstance(content, list):
            content = [content_block_from_dict(block) if isinstance(block, dict) else block for block in content]
        return cls(role=data.get("role", "user"), content=content)


@dataclass
class MessageMetadata:
    timestamp: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    tokens: Optional[int] = None
    extra: dict = field(default_factory=dict)
