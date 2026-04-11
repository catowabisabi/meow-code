"""Tool models for the tool system."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict = field(default_factory=dict)

    def model_dump(self, **kwargs) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        return cls(id=data.get("id", ""), name=data.get("name", ""), arguments=data.get("arguments", {}))


@dataclass
class ToolResult:
    tool_call_id: str
    output: str
    is_error: bool = False

    def model_dump(self, **kwargs) -> dict:
        return {"tool_call_id": self.tool_call_id, "output": self.output, "is_error": self.is_error}

    @classmethod
    def from_dict(cls, data: dict) -> "ToolResult":
        return cls(tool_call_id=data.get("tool_call_id", ""), output=data.get("output", ""), is_error=data.get("is_error", False))


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    is_read_only: bool = False

    def model_dump(self, **kwargs) -> dict:
        return {"name": self.name, "description": self.description, "inputSchema": self.input_schema, "isReadOnly": self.is_read_only}

    @classmethod
    def from_dict(cls, data: dict) -> "ToolDefinition":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", data.get("input_schema", {})),
            is_read_only=data.get("isReadOnly", data.get("is_read_only", False))
        )


@dataclass
class ToolInfo:
    name: str
    description: str
    is_read_only: bool = False
    risk_level: str = "low"
    input_schema: Optional[dict] = None

    def model_dump(self, **kwargs) -> dict:
        return {"name": self.name, "description": self.description, "isReadOnly": self.is_read_only, "riskLevel": self.risk_level, "inputSchema": self.input_schema}

    @classmethod
    def from_dict(cls, data: dict) -> "ToolInfo":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            is_read_only=data.get("isReadOnly", data.get("is_read_only", False)),
            risk_level=data.get("riskLevel", "low"),
            input_schema=data.get("inputSchema", data.get("input_schema"))
        )
