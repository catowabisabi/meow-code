"""
Base adapter classes for AI provider adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional, Dict, Any

from ..models.message import Message
from ..models.tool import ToolDefinition


@dataclass
class ChatEvent:
    """
    Unified chat event format for streaming responses.
    
    Event types:
        - stream_start: Sent at the beginning of a stream
        - stream_text_delta: Text content delta
        - stream_thinking_delta: Thinking content delta (for models that support it)
        - stream_tool_use_start: Tool use started
        - stream_tool_use_delta: Tool use input delta
        - stream_tool_use_end: Tool use completed
        - stream_end: Stream completed
        - stream_error: Stream error occurred
    """
    type: str  # "stream_start" | "stream_text_delta" | "stream_thinking_delta" | "stream_tool_use_start" | "stream_tool_use_delta" | "stream_tool_use_end" | "stream_end" | "stream_error"
    
    # Common fields
    message_id: Optional[str] = None
    session_id: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    
    # Text/Thinking delta fields
    text: Optional[str] = None
    
    # Tool use fields
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input_delta: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    
    # End/Error fields
    stop_reason: Optional[str] = None
    error: Optional[str] = None
    
    # Index for ordering
    index: int = 0
    
    @classmethod
    def stream_start(
        cls,
        message_id: str,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        index: int = 0,
    ) -> "ChatEvent":
        """Create a stream_start event."""
        return cls(
            type="stream_start",
            message_id=message_id,
            session_id=session_id,
            model=model,
            provider=provider,
            index=index,
        )
    
    @classmethod
    def text_delta(cls, text: str, index: int = 0) -> "ChatEvent":
        """Create a stream_text_delta event."""
        return cls(type="stream_text_delta", text=text, index=index)
    
    @classmethod
    def thinking_delta(cls, text: str, index: int = 0) -> "ChatEvent":
        """Create a stream_thinking_delta event."""
        return cls(type="stream_thinking_delta", text=text, index=index)
    
    @classmethod
    def tool_use_start(
        cls,
        tool_id: str,
        tool_name: str,
        index: int = 0,
    ) -> "ChatEvent":
        """Create a stream_tool_use_start event."""
        return cls(
            type="stream_tool_use_start",
            tool_id=tool_id,
            tool_name=tool_name,
            index=index,
        )
    
    @classmethod
    def tool_use_delta(
        cls,
        tool_id: str,
        tool_input_delta: str,
        index: int = 0,
    ) -> "ChatEvent":
        """Create a stream_tool_use_delta event."""
        return cls(
            type="stream_tool_use_delta",
            tool_id=tool_id,
            tool_input_delta=tool_input_delta,
            index=index,
        )
    
    @classmethod
    def tool_use_end(
        cls,
        tool_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        index: int = 0,
    ) -> "ChatEvent":
        """Create a stream_tool_use_end event."""
        return cls(
            type="stream_tool_use_end",
            tool_id=tool_id,
            tool_name=tool_name,
            tool_input=tool_input,
            index=index,
        )
    
    @classmethod
    def stream_end(
        cls,
        stop_reason: Optional[str] = None,
        index: int = 0,
    ) -> "ChatEvent":
        """Create a stream_end event."""
        return cls(type="stream_end", stop_reason=stop_reason, index=index)
    
    @classmethod
    def stream_error(cls, error: str, index: int = 0) -> "ChatEvent":
        """Create a stream_error event."""
        return cls(type="stream_error", error=error, index=index)
    
    def model_dump(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        result: Dict[str, Any] = {"type": self.type}
        
        if self.message_id is not None:
            result["messageId"] = self.message_id
        if self.session_id is not None:
            result["sessionId"] = self.session_id
        if self.model is not None:
            result["model"] = self.model
        if self.provider is not None:
            result["provider"] = self.provider
        if self.text is not None:
            result["text"] = self.text
        if self.tool_id is not None:
            result["toolId"] = self.tool_id
        if self.tool_name is not None:
            result["toolName"] = self.tool_name
        if self.tool_input_delta is not None:
            result["inputDelta"] = self.tool_input_delta
        if self.tool_input is not None:
            result["toolInput"] = self.tool_input
        if self.stop_reason is not None:
            result["stopReason"] = self.stop_reason
        if self.error is not None:
            result["error"] = self.error
        if self.index != 0:
            result["index"] = self.index
            
        return result


class BaseAdapter(ABC):
    """
    Abstract base class for AI provider adapters.
    
    All adapters must implement:
        - chat(): Stream chat completions
        - test_connection(): Test API connection
    """
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: str,
        system_prompt: str,
        tools: List[ToolDefinition],
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[ChatEvent]:
        """
        Stream chat completions from the AI provider.
        
        Args:
            messages: List of conversation messages
            model: Model identifier to use
            system_prompt: System prompt to prepend
            tools: List of available tools
            stream: Whether to stream the response
            **kwargs: Additional provider-specific arguments
            
        Yields:
            ChatEvent objects representing the stream
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test the connection to the AI provider.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
