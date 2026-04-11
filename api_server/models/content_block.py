"""Content block models for unified multi-model adapter."""
from dataclasses import dataclass, field
from typing import Union, List


@dataclass
class TextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class ThinkingBlock:
    type: str = "thinking"
    text: str = ""


@dataclass
class ToolUseBlock:
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class ToolResultBlock:
    type: str = "tool_result"
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False


@dataclass
class ImageBlock:
    type: str = "image"
    source: dict = field(default_factory=lambda: {"type": "base64", "media_type": "", "data": ""})

    def model_dump(self, **kwargs) -> dict:
        return {"type": self.type, "source": self.source}


ContentBlock = Union[TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock, ImageBlock, dict]


def content_block_from_dict(data: dict) -> ContentBlock:
    if not isinstance(data, dict):
        return data
    
    block_type = data.get("type", "text")
    
    if block_type == "text":
        return TextBlock(type="text", text=data.get("text", ""))
    elif block_type == "thinking":
        return ThinkingBlock(type="thinking", text=data.get("text", ""))
    elif block_type == "tool_use":
        return ToolUseBlock(type="tool_use", id=data.get("id", ""), name=data.get("name", ""), input=data.get("input", {}))
    elif block_type == "tool_result":
        return ToolResultBlock(type="tool_result", tool_use_id=data.get("tool_use_id", ""), content=data.get("content", ""), is_error=data.get("is_error", False))
    elif block_type == "image":
        return ImageBlock(type="image", source=data.get("source", {}))
    
    return data


class ContentBlockSerializer:
    @staticmethod
    def serialize(block: ContentBlock) -> dict:
        if isinstance(block, dict):
            return block
        if hasattr(block, 'model_dump'):
            return block.model_dump()
        if hasattr(block, '__dict__'):
            return block.__dict__
        return block

    @staticmethod
    def serialize_content(content: Union[str, List[ContentBlock]]) -> Union[str, List[dict]]:
        if isinstance(content, str):
            return content
        return [ContentBlockSerializer.serialize(block) for block in content]
