"""
Ollama adapter for local model inference.
"""
import uuid
from typing import AsyncIterator, List

import httpx

from ..models.message import Message
from ..models.tool import ToolDefinition
from .base import BaseAdapter, ChatEvent


class OllamaAdapter(BaseAdapter):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = "llama3"
    
    async def chat(
        self,
        messages: List[Message],
        model: str,
        system_prompt: str,
        tools: List[ToolDefinition],
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator[ChatEvent]:
        model = model or self.default_model
        
        if system_prompt:
            messages = [Message(role="system", content=system_prompt)] + messages
        
        ollama_messages = self._convert_messages(messages)
        
        tool_params = None
        if tools:
            tool_params = {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.input_schema,
                        }
                    }
                    for tool in tools
                ]
            }
        
        index = 0
        message_id = str(uuid.uuid4())
        
        yield ChatEvent.stream_start(
            message_id=message_id,
            model=model,
            provider="ollama",
            index=index,
        )
        index += 1
        
        request_data = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
        }
        
        if tool_params:
            request_data["tools"] = tool_params["tools"]
        
        if kwargs.get("temperature"):
            request_data["temperature"] = kwargs["temperature"]
        if kwargs.get("options"):
            request_data["options"] = kwargs["options"]
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=request_data,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        import json
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        
                        msg_type = chunk.get("done", False)
                        
                        if chunk.get("message"):
                            content = chunk["message"].get("content", "")
                            if content:
                                yield ChatEvent.text_delta(text=content, index=index)
                                index += 1
                        
                        if chunk.get("tool_calls"):
                            for tool_call in chunk["tool_calls"]:
                                yield ChatEvent.tool_use_end(
                                    tool_id=tool_call.get("id", str(uuid.uuid4())),
                                    tool_name=tool_call.get("function", {}).get("name", ""),
                                    tool_input=tool_call.get("function", {}).get("arguments", {}),
                                    index=index,
                                )
                                index += 1
                        
                        if msg_type:
                            stop_reason = chunk.get("done_reason", "stop")
                            yield ChatEvent.stream_end(
                                stop_reason=stop_reason,
                                index=index,
                            )
                            index += 1
        except Exception as e:
            yield ChatEvent.stream_error(error=str(e), index=index)
    
    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def _convert_messages(self, messages: List[Message]) -> List[dict]:
        result = []
        for msg in messages:
            if isinstance(msg, Message):
                content = msg.content
                if isinstance(content, str):
                    msg_dict = {"role": msg.role, "content": content}
                else:
                    from ..models.content_block import ContentBlockSerializer
                    serialized_content = ContentBlockSerializer.serialize_content(content)
                    msg_dict = {"role": msg.role, "content": serialized_content}
            else:
                msg_dict = msg
            
            result.append(msg_dict)
        return result
