"""
Anthropic (Claude) adapter using the official SDK.
"""
import uuid
from typing import AsyncIterator, List

from anthropic import AsyncAnthropic

from ..models.message import Message
from ..models.tool import ToolDefinition
from .base import BaseAdapter, ChatEvent


class AnthropicAdapter(BaseAdapter):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout: float = 60.0,
    ):
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.default_model = "claude-sonnet-4-20250514"
    
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
        
        system_message = system_prompt if system_prompt else None
        
        anthropic_messages = self._convert_messages(messages)
        
        tool_params = None
        if tools:
            tool_params = [
                {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "input_schema": tool_def.input_schema,
                }
                for tool_def in tools
            ]
        
        index = 0
        message_id = str(uuid.uuid4())
        
        yield ChatEvent.stream_start(
            message_id=message_id,
            model=model,
            provider="anthropic",
            index=index,
        )
        index += 1
        
        if stream:
            async with self.client.messages.stream(
                model=model,
                system=system_message,
                messages=anthropic_messages,
                tools=tool_params,
                max_tokens=kwargs.get("max_tokens", 4096),
            ) as stream:
                async for text_chunk in stream.text_stream:
                    yield ChatEvent.text_delta(text=text_chunk, index=index)
                    index += 1
                
                if tool_params:
                    async for tool_chunk in stream.tool_use_stream:
                        if tool_chunk.type == "tool_use_start":
                            yield ChatEvent.tool_use_start(
                                tool_id=tool_chunk.id,
                                tool_name=tool_chunk.name,
                                index=index,
                            )
                            index += 1
                        elif tool_chunk.type == "tool_use_delta":
                            if hasattr(tool_chunk, 'partial_json') and tool_chunk.partial_json:
                                yield ChatEvent.tool_use_delta(
                                    tool_id=tool_chunk.id,
                                    tool_input_delta=tool_chunk.partial_json,
                                    index=index,
                                )
                                index += 1
                
                message = await stream.get_final_message()
                
                for tool_use in message.tool_calls or []:
                    yield ChatEvent.tool_use_end(
                        tool_id=tool_use.id,
                        tool_name=tool_use.name,
                        tool_input=tool_use.input,
                        index=index,
                    )
                    index += 1
                
                yield ChatEvent.stream_end(
                    stop_reason=message.stop_reason,
                    index=index,
                )
        else:
            response = await self.client.messages.create(
                model=model,
                system=system_message,
                messages=anthropic_messages,
                tools=tool_params,
                max_tokens=kwargs.get("max_tokens", 4096),
            )
            
            for content in response.content:
                if content.type == "text":
                    yield ChatEvent.text_delta(text=content.text, index=index)
                    index += 1
                elif content.type == "tool_use":
                    yield ChatEvent.tool_use_end(
                        tool_id=content.id,
                        tool_name=content.name,
                        tool_input=content.input,
                        index=index,
                    )
                    index += 1
            
            yield ChatEvent.stream_end(
                stop_reason=response.stop_reason,
                index=index,
            )
    
    async def test_connection(self) -> bool:
        try:
            await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1,
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
