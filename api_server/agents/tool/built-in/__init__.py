from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BuiltInAgent:
    agent_type: str
    when_to_use: str
    tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    model: Optional[str] = None
    omit_claude_md: bool = False
    background: bool = False
    color: Optional[str] = None
    permission_mode: Optional[str] = None
    source: str = "built-in"
    max_turns: Optional[int] = None
    effort: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    hooks: list = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    critical_system_reminder: Optional[str] = None
    
    def get_system_prompt(self, tool_use_context=None) -> str:
        raise NotImplementedError("Subclasses must implement get_system_prompt")
    
    def to_definition(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "when_to_use": self.when_to_use,
            "tools": self.tools,
            "disallowed_tools": self.disallowed_tools,
            "model": self.model,
            "omit_claude_md": self.omit_claude_md,
            "background": self.background,
            "color": self.color,
            "permission_mode": self.permission_mode,
            "source": self.source,
            "max_turns": self.max_turns,
            "effort": self.effort,
            "skills": self.skills,
            "hooks": self.hooks,
            "mcp_servers": self.mcp_servers,
            "critical_system_reminder": self.critical_system_reminder,
            "system_prompt": self.get_system_prompt(),
        }
