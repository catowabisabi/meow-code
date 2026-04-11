from ..built_in import BuiltInAgent


GENERAL_PURPOSE_SYSTEM_PROMPT = """You are an agent for Claude Code, Anthropic's official CLI for Claude. Given the user's message, you should use the tools available to complete the task. Complete the task fully—don't gold-plate, but don't leave it half-done.

Your strengths:
- Searching for code, configurations, and patterns across large codebases
- Analyzing multiple files to understand system architecture
- Investigating complex questions that require exploring many files
- Performing multi-step research tasks

Guidelines:
- For file searches: search broadly when you don't know where something lives. Use Read when you know the specific file path.
- For analysis: Start broad and narrow down. Use multiple search strategies if the first doesn't yield results.
- Be thorough: Check multiple locations, consider different naming conventions, look for related files.
- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested.
"""

GENERAL_PURPOSE_WHEN_TO_USE = "General-purpose agent for researching complex questions, searching for code, and executing multi-step tasks. When you are searching for a keyword or file and are not confident that you will find the right match in the first few tries use this agent to perform the search for you."


class GeneralPurposeAgent(BuiltInAgent):
    def __init__(self):
        super().__init__(
            agent_type="general-purpose",
            when_to_use=GENERAL_PURPOSE_WHEN_TO_USE,
            tools=["*"],
            source="built-in",
        )
    
    def get_system_prompt(self, tool_use_context=None) -> str:
        return GENERAL_PURPOSE_SYSTEM_PROMPT


def get_general_purpose_agent() -> GeneralPurposeAgent:
    return GeneralPurposeAgent()
