"""
Periodic background summarization for coordinator mode sub-agents.

Generates a 3-5 word present-tense summary every ~30s using the Haiku model.
The summary is pushed via WebSocket for UI display.

Architecture:
- Uses asyncio timer (not threading.Timer)
- Stores agent messages in memory for summarization
- Uses query_haiku() directly (not runForkedAgent)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from .api.claude import query_haiku, get_anthropic_client, QueryHaikuOptions

SUMMARY_INTERVAL_MS = 30_000

# System prompt for generating agent summaries
AGENT_SUMMARY_SYSTEM_PROMPT = "You are a helpful assistant that summarizes agent actions."


def build_summary_prompt(previous_summary: Optional[str]) -> str:
    """
    Build the user prompt for summarizing agent actions.

    Args:
        previous_summary: The previous summary to indicate "say something NEW"

    Returns:
        Formatted prompt string
    """
    prev_line = ""
    if previous_summary:
        prev_line = f'\nPrevious: "{previous_summary}" — say something NEW.\n'

    return f'''Describe your most recent action in 3-5 words using present tense (-ing). Name the file or function, not the branch. Do not use tools.
{prev_line}
Good: "Reading runAgent.ts"
Good: "Fixing null check in validate.ts"
Good: "Running auth module tests"
Good: "Adding retry logic to fetchUser"

Bad (past tense): "Analyzed the branch diff"
Bad (too vague): "Investigating the issue"
Bad (too long): "Reviewing full branch diff and AgentTool.tsx integration"
Bad (branch name): "Analyzed adam/background-summary branch diff"
'''


async def generate_agent_summary(
    messages: List[Dict[str, Any]],
    previous_summary: Optional[str] = None,
    signal: Optional[Any] = None,
) -> Optional[str]:
    """
    Generate a 3-5 word present-tense summary using Haiku.

    Args:
        messages: List of conversation messages
        previous_summary: Previous summary to indicate "say something NEW"
        signal: Optional abort signal

    Returns:
        Summary text (3-5 words, present tense) or None if generation failed
    """
    if len(messages) < 3:
        return None

    prompt = build_summary_prompt(previous_summary)

    try:
        client = await get_anthropic_client()

        response = await query_haiku(
            client,
            QueryHaikuOptions(
                system_prompt=AGENT_SUMMARY_SYSTEM_PROMPT,
                user_prompt=prompt,
                signal=signal,
                query_source="agent_summary",
                enable_prompt_caching=True,
                is_non_interactive_session=True,
            ),
        )

        # Extract summary text from response
        content = response.get("message", {}).get("content", [])
        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "").strip()
                if text:
                    return text

        return None

    except Exception as e:
        logging.error(f"Agent summary generation failed: {e}")
        return None


class AgentSummaryService:
    """
    Manages periodic summarization tasks for agents.

    Uses asyncio timers for periodic summarization and pushes
    summaries via WebSocket.
    """

    _tasks: Dict[str, asyncio.Task] = {}
    _previous_summaries: Dict[str, Optional[str]] = {}
    _abort_controllers: Dict[str, asyncio.Event] = {}
    _stop_flags: Dict[str, bool] = {}
    # In-memory storage for agent messages: agent_id -> messages
    _agent_messages: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def add_message(cls, agent_id: str, message: Dict[str, Any]) -> None:
        """Add a message to the agent's conversation history."""
        if agent_id not in cls._agent_messages:
            cls._agent_messages[agent_id] = []
        cls._agent_messages[agent_id].append(message)

    @classmethod
    def get_messages(cls, agent_id: str) -> List[Dict[str, Any]]:
        """Get all messages for an agent."""
        return cls._agent_messages.get(agent_id, [])

    @classmethod
    def clear_messages(cls, agent_id: str) -> None:
        """Clear all messages for an agent."""
        cls._agent_messages.pop(agent_id, None)

    @classmethod
    async def start(
        cls,
        agent_id: str,
        session_id: Optional[str],
        websocket: Any,
    ) -> None:
        """
        Start periodic summarization for an agent.

        Args:
            agent_id: Unique identifier for the agent
            session_id: Session identifier (optional, for future use)
            websocket: WebSocket to send summaries to
        """
        # Stop any existing task for this agent
        cls.stop(agent_id)

        cls._stop_flags[agent_id] = False
        cls._previous_summaries[agent_id] = None

        # Create abort controller for this agent
        abort_event = asyncio.Event()
        cls._abort_controllers[agent_id] = abort_event

        # Schedule the first summary
        async def run_and_schedule():
            await cls._run_summary(agent_id, session_id, websocket)
            if not cls._stop_flags.get(agent_id, False):
                # Schedule next iteration
                await asyncio.sleep(SUMMARY_INTERVAL_MS / 1000)
                if not cls._stop_flags.get(agent_id, False):
                    asyncio.create_task(run_and_schedule())

        cls._tasks[agent_id] = asyncio.create_task(run_and_schedule())

        logging.debug(f"[AgentSummary] Started summarization for agent {agent_id}")

    @classmethod
    def stop(cls, agent_id: str) -> None:
        """
        Stop periodic summarization for an agent.

        Args:
            agent_id: Unique identifier for the agent
        """
        cls._stop_flags[agent_id] = True

        # Cancel existing task
        task = cls._tasks.pop(agent_id, None)
        if task and not task.done():
            task.cancel()

        # Abort any in-progress summary
        abort_event = cls._abort_controllers.pop(agent_id, None)
        if abort_event:
            abort_event.set()

        # Clean up previous summary
        cls._previous_summaries.pop(agent_id, None)

        logging.debug(f"[AgentSummary] Stopped summarization for agent {agent_id}")

    @classmethod
    async def _run_summary(
        cls,
        agent_id: str,
        session_id: Optional[str],
        websocket: Any,
    ) -> None:
        """
        Single summary iteration.

        Gets messages, generates summary via Haiku, and sends via WebSocket.

        Args:
            agent_id: Unique identifier for the agent
            session_id: Session identifier
            websocket: WebSocket to send summaries to
        """
        if cls._stop_flags.get(agent_id, False):
            return

        logging.debug(f"[AgentSummary] Timer fired for agent {agent_id}")

        try:
            messages = cls.get_messages(agent_id)
            if len(messages) < 3:
                logging.debug(
                    f"[AgentSummary] Skipping summary for {agent_id}: "
                    f"not enough messages ({len(messages)})"
                )
                return

            abort_event = cls._abort_controllers.get(agent_id)
            signal = abort_event if abort_event else None

            summary_text = await generate_agent_summary(
                messages=messages,
                previous_summary=cls._previous_summaries.get(agent_id),
                signal=signal,
            )

            if cls._stop_flags.get(agent_id, False):
                return

            if summary_text:
                cls._previous_summaries[agent_id] = summary_text
                logging.debug(f"[AgentSummary] Summary result for {agent_id}: {summary_text}")

                # Send summary via WebSocket
                await websocket.send_json({
                    "type": "agent_summary",
                    "agentId": agent_id,
                    "summary": summary_text,
                })

        except Exception as e:
            if not cls._stop_flags.get(agent_id, False):
                logging.error(f"[AgentSummary] Error generating summary for {agent_id}: {e}")


# Global instance for convenience
service = AgentSummaryService()
