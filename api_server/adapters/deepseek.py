"""
DeepSeek adapter using OpenAI-compatible API.
"""
import uuid
from typing import AsyncIterator, List

from openai import AsyncOpenAI

from ..models.message import Message
from ..models.tool import ToolDefinition
from .base import BaseAdapter, ChatEvent


class DeepSeekAdapter(BaseAdapter):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout: float = 60.0,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.default_model = "deepseek-chat"
    
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
        
        openai_messages = self._convert_messages(messages)
        
        tool_params = None
        if tools:
            tool_params = [
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
        
        index = 0
        message_id = str(uuid.uuid4())
        
        yield ChatEvent.stream_start(
            message_id=message_id,
            model=model,
            provider="deepseek",
            index=index,
        )
        index += 1
        
        stream_params = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
        }
        
        if tool_params:
            stream_params["tools"] = tool_params
        
        if kwargs.get("temperature"):
            stream_params["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens"):
            stream_params["max_tokens"] = kwargs["max_tokens"]
        
        try:
            async with self.client.chat.completions.create(**stream_params) as stream_response:
                assistant_message_id = None
                async for chunk in stream_response:
                    if not chunk.choices:
                        continue
                    
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    if delta.content:
                        yield ChatEvent.text_delta(text=delta.content, index=index)
                        index += 1
                    
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            if tool_call.id:
                                assistant_message_id = tool_call.id
                                yield ChatEvent.tool_use_start(
                                    tool_id=tool_call.id,
                                    tool_name=tool_call.function.name if tool_call.function else "",
                                    index=index,
                                )
                                index += 1
                            
                            if tool_call.function and tool_call.function.arguments:
                                yield ChatEvent.tool_use_delta(
                                    tool_id=tool_call.id or assistant_message_id or "",
                                    tool_input_delta=tool_call.function.arguments,
                                    index=index,
                                )
                                index += 1
                    
                    if choice.finish_reason:
                        yield ChatEvent.stream_end(
                            stop_reason=choice.finish_reason,
                            index=index,
                        )
                        index += 1
        except Exception as e:
            yield ChatEvent.stream_error(error=str(e), index=index)
    
    async def test_connection(self) -> bool:
        try:
            await self.client.chat.completions.create(
                model=self.default_model,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
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
