import json
import logging
from dataclasses import dataclass
from typing import Optional, Any, List

from .api.claude import query_haiku, get_anthropic_client, QueryHaikuOptions


TOOL_USE_SUMMARY_SYSTEM_PROMPT = """Write a short summary label describing what these tool calls accomplished. It appears as a single-line row in a mobile app and truncates around 30 characters, so think git-commit-subject, not sentence.

Keep the verb in past tense and the most distinctive noun. Drop articles, connectors, and long location context first.

Examples:
- Searched in auth/
- Fixed NPE in UserService
- Created signup endpoint
- Read config.json
- Ran failing tests"""


@dataclass
class ToolInfo:
    name: str
    input: Any
    output: Any


@dataclass
class GenerateToolUseSummaryParams:
    tools: List[ToolInfo]
    signal: Optional[Any] = None
    is_non_interactive_session: bool = False
    last_assistant_text: Optional[str] = None


def truncate_json(value: Any, max_length: int) -> str:
    try:
        str_value = json.dumps(value)
        if len(str_value) <= max_length:
            return str_value
        return str_value[:max_length - 3] + "..."
    except (TypeError, ValueError):
        return "[unable to serialize]"


async def generate_tool_use_summary(
    params: GenerateToolUseSummaryParams,
) -> Optional[str]:
    if len(params.tools) == 0:
        return None

    try:
        tool_summaries = []
        for tool in params.tools:
            input_str = truncate_json(tool.input, 300)
            output_str = truncate_json(tool.output, 300)
            tool_summaries.append(f"Tool: {tool.name}\nInput: {input_str}\nOutput: {output_str}")

        tool_summaries_text = "\n\n".join(tool_summaries)

        context_prefix = ""
        if params.last_assistant_text:
            context_prefix = f"User's intent (from assistant's last message): {params.last_assistant_text[:200]}\n\n"

        user_prompt = f"{context_prefix}Tools completed:\n\n{tool_summaries_text}\n\nLabel:"

        client = await get_anthropic_client()

        response = await query_haiku(
            client,
            QueryHaikuOptions(
                system_prompt=TOOL_USE_SUMMARY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                signal=params.signal,
                query_source="tool_use_summary_generation",
                enable_prompt_caching=True,
                is_non_interactive_session=params.is_non_interactive_session,
            ),
        )

        content = response.get("message", {}).get("content", [])
        summary = ""
        for block in content:
            if block.get("type") == "text":
                summary += block.get("text", "")

        summary = summary.strip()
        return summary if summary else None

    except Exception as error:
        logging.error(f"Tool use summary generation failed: {error}")
        return None