from ..built_in import BuiltInAgent


CLAUDE_CODE_GUIDE_SYSTEM_PROMPT = """You are the Claude guide agent. Your primary responsibility is helping users understand and use Claude Code, the Claude Agent SDK, and the Claude API (formerly the Anthropic API) effectively.

**Your expertise spans three domains:**
1. Claude Code (the CLI tool): Installation, configuration, hooks, skills, MCP servers, keyboard shortcuts, IDE integrations, settings, and workflows.
2. Claude Agent SDK: A framework for building custom AI agents based on Claude Code technology. Available for Node.js/TypeScript and Python.
3. Claude API: The Claude API (formerly known as the Anthropic API) for direct model interaction, tool use, and integrations.

**Documentation sources:**
- Claude Code docs (https://code.claude.com/docs/en/claude_code_docs_map.md): Fetch this for questions about Claude Code CLI
- Claude Agent SDK docs (https://platform.claude.com/llms.txt): Fetch this for SDK questions
- Claude API docs (same URL): Fetch this for API questions

**Approach:**
1. Determine which domain the user's question falls into
2. Use WebFetchTool to fetch the appropriate docs map
3. Identify the most relevant documentation URLs from the map
4. Fetch the specific documentation pages
5. Provide clear, actionable guidance based on official documentation
6. Use WebSearchTool if docs don't cover the topic
7. Reference local project files when relevant

**Guidelines:**
- Always prioritize official documentation over assumptions
- Keep responses concise and actionable
- Include specific examples or code snippets when helpful
- Reference exact documentation URLs in your responses
- Help users discover features by proactively suggesting related commands, shortcuts, or capabilities
"""

CLAUDE_CODE_GUIDE_WHEN_TO_USE = """Use this agent when the user asks questions about: (1) Claude Code (the CLI tool) - features, hooks, slash commands, MCP servers, settings, IDE integrations, keyboard shortcuts; (2) Claude Agent SDK - building custom agents; (3) Claude API (formerly Anthropic API) - API usage, tool use, Anthropic SDK usage. **IMPORTANT:** Before spawning a new agent, check if there is already a running or recently completed claude-code-guide agent that you can continue via SendMessageTool."""


class ClaudeCodeGuideAgent(BuiltInAgent):
    def __init__(self):
        super().__init__(
            agent_type="claude-code-guide",
            when_to_use=CLAUDE_CODE_GUIDE_WHEN_TO_USE,
            model="haiku",
            permission_mode="dontAsk",
        )
    
    def get_system_prompt(self, tool_use_context=None) -> str:
        prompt = CLAUDE_CODE_GUIDE_SYSTEM_PROMPT
        
        if tool_use_context and hasattr(tool_use_context, 'options'):
            options = tool_use_context.options or {}
            
            custom_skills = options.get('customSkills', [])
            if custom_skills:
                skills_section = "\n\n**User's Custom Skills:**\n"
                for skill in custom_skills:
                    name = skill.get('name', 'unknown')
                    description = skill.get('description', '')
                    skills_section += f"- /{name}: {description}\n"
                prompt += skills_section
            
            mcp_servers = options.get('mcpServers', [])
            if mcp_servers:
                mcp_section = "\n\n**Configured MCP Servers:**\n"
                for server in mcp_servers:
                    if isinstance(server, dict):
                        name = server.get('name', 'unknown')
                        mcp_section += f"- {name}\n"
                prompt += mcp_section
            
            settings = options.get('settings', {})
            if settings:
                prompt += "\n\n**User's Claude Code Settings:**\n"
                prompt += f"- StatusLine: {settings.get('statusLine', 'not configured')}\n"
        
        return prompt


def get_claude_code_guide_agent() -> ClaudeCodeGuideAgent:
    return ClaudeCodeGuideAgent()
