"""
AI-powered session title generator.
After each conversation turn, sends the current title + recent messages
to the AI and asks it to decide if a better title is needed.
Returns the new title or None (keep current).
"""
import json
import re
from typing import AsyncGenerator, List, Optional, Union

from pydantic import BaseModel


class ContentBlock(BaseModel):
    type: str
    text: Optional[str] = None


class Message(BaseModel):
    role: str
    content: Union[str, List[ContentBlock], List[dict]]


async def _route_chat(
    messages: List[Message], model: str, provider: str, stream: bool = False
) -> AsyncGenerator[dict, None]:
    """
    Route chat to AI provider.
    
    This is a placeholder that yields mock events.
    Replace with actual AI adapter integration.
    """
    yield {"type": "stream_text_delta", "text": '{"new_topic": "N/A"}'}
    yield {"type": "stream_end", "stop_reason": "end_turn"}


async def generate_smart_title(
    current_title: str,
    messages: List[Message],
    model: str,
    provider: str,
) -> Optional[str]:
    try:
        recent_messages = messages[-6:]

        def extract_text(msg: Message) -> str:
            role = "User" if msg.role == "user" else "Assistant"
            text = ""

            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        break
                    elif hasattr(block, "type") and block.type == "text":
                        text = block.text
                        break

            if len(text) > 200:
                text = text[:200] + "..."

            return f"{role}: {text}"

        summary = "\n".join(extract_text(m) for m in recent_messages)

        prompt = f"""You are a conversation topic generator. Based on the conversation below, decide if the topic should be updated.

existing_topic: "{current_title}"

Conversation:
{summary}

Respond with ONLY valid JSON — no explanation, no markdown, no text outside the JSON:
{{ "new_topic": "your new topic here" }}

Rules:
- If existing_topic already describes the conversation well, respond: {{ "new_topic": "N/A" }}
- Use SAME LANGUAGE as the user's messages
- new_topic must be 15 characters or fewer
- Do NOT include any text outside the JSON block"""

        request_messages = [Message(role="user", content=prompt)]

        response_text = ""
        async for event in _route_chat(request_messages, model, provider, stream=False):
            if event.get("type") == "stream_text_delta":
                response_text += event.get("text", "")
            elif event.get("type") == "stream_error":
                return None

        result = response_text.strip()

        json_match = re.search(r"\{[^}]+\}", result)
        if not json_match:
            return None

        try:
            parsed = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return None

        new_topic = parsed.get("new_topic")

        if not new_topic or new_topic == "N/A" or new_topic == current_title:
            return None

        return new_topic[:30] if len(new_topic) > 30 else new_topic

    except Exception:
        return None
