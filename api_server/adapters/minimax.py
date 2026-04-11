"""
MiniMax adapter using OpenAI-compatible API.
"""
import json
import uuid
from typing import AsyncIterator, List

from openai import AsyncOpenAI

from ..models.message import Message
from ..models.tool import ToolDefinition
from .base import BaseAdapter, ChatEvent


class MiniMaxAdapter(BaseAdapter):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.minimax.io/v1",
        timeout: float = 60.0,
        group_id: str = None,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self.default_model = "MiniMax-Text-01"
        self.group_id = group_id
    
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
            provider="minimax",
            index=index,
        )
        index += 1
        
        extra_headers = None
        if self.group_id:
            extra_headers = {"group-id": self.group_id}
        
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
            stream_response = await self.client.chat.completions.create(
                **stream_params,
                extra_headers=extra_headers,
            )
            # Track accumulated tool calls: {index: {id, name, arguments}}
            accumulated_tools: dict[int, dict] = {}

            async for chunk in stream_response:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    yield ChatEvent.text_delta(text=delta.content, index=index)
                    index += 1

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tc_idx = tc.index if tc.index is not None else 0
                        if tc_idx not in accumulated_tools:
                            accumulated_tools[tc_idx] = {
                                "id": tc.id or str(uuid.uuid4()),
                                "name": "",
                                "arguments": "",
                            }
                        acc = accumulated_tools[tc_idx]
                        if tc.id:
                            acc["id"] = tc.id
                        if tc.function and tc.function.name:
                            acc["name"] = tc.function.name
                            yield ChatEvent.tool_use_start(
                                tool_id=acc["id"],
                                tool_name=acc["name"],
                                index=index,
                            )
                            index += 1
                        if tc.function and tc.function.arguments:
                            acc["arguments"] += tc.function.arguments
                            yield ChatEvent.tool_use_delta(
                                tool_id=acc["id"],
                                tool_input_delta=tc.function.arguments,
                                index=index,
                            )
                            index += 1

                if choice.finish_reason:
                    # Finalize any accumulated tool calls
                    for acc in accumulated_tools.values():
                        try:
                            parsed_input = json.loads(acc["arguments"]) if acc["arguments"] else {}
                        except json.JSONDecodeError:
                            parsed_input = {"raw": acc["arguments"]}
                        yield ChatEvent.tool_use_end(
                            tool_id=acc["id"],
                            tool_name=acc["name"],
                            tool_input=parsed_input,
                            index=index,
                        )
                        index += 1

                    # Map OpenAI finish reasons to Anthropic-style
                    stop = choice.finish_reason
                    if stop == "tool_calls":
                        stop = "tool_use"
                    yield ChatEvent.stream_end(
                        stop_reason=stop,
                        index=index,
                    )
                    index += 1
        except Exception as e:
            yield ChatEvent.stream_error(error=str(e), index=index)
    
    async def test_connection(self) -> bool:
        try:
            extra_headers = {"group-id": self.group_id} if self.group_id else None
            await self.client.chat.completions.create(
                model=self.default_model,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}],
                extra_headers=extra_headers,
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
