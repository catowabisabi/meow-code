"""Tool registration - imports and registers all tools."""
from api_server.tools.executor import register_tool
from api_server.tools.file_tools import FILE_TOOLS
from api_server.tools.shell import shell_tool
from api_server.tools.web_tools import web_fetch_tool, web_search_tool
from api_server.tools.agent_tools import AGENT_TOOLS
from api_server.tools.todo_tool import todo_write_tool
from api_server.tools.notebook_edit import TOOL_NOTEBOOK_EDIT
from api_server.tools.todo_write import TOOL_TODO_WRITE
from api_server.tools.memory_tools import memory_read_tool, memory_write_tool
from api_server.tools.plan_tool import enter_plan_mode_tool, exit_plan_mode_tool
from api_server.tools.brief_tool import BRIEF_TOOL
from api_server.tools.brief import TOOL_BRIEF
from api_server.tools.ask_user_question import TOOL_ASK_USER_QUESTION
from api_server.tools.sleep_tool import SLEEP_TOOL
from api_server.tools.sleep import TOOL_SLEEP
from api_server.tools.ask_user_tool import ASK_USER_TOOL
from api_server.tools.config_tool import TOOL_CONFIG_GET, TOOL_CONFIG_SET
from api_server.tools.task_create import TaskCreateTool
from api_server.tools.task_get import TaskGetTool
from api_server.tools.task_list import TaskListTool
from api_server.tools.task_update import TaskUpdateTool
from api_server.tools.task_stop import TaskStopTool
from api_server.tools.task_output import TaskOutputTool
from api_server.tools.web_search import WebSearchTool
from api_server.tools.web_fetch import WebFetchTool
from api_server.tools.worktree_tools import (
    ENTER_WORKTREE_TOOL,
    EXIT_WORKTREE_TOOL,
    LIST_WORKTREES_TOOL,
)
from api_server.tools.tool_search_tool import TOOL_SEARCH_TOOL
from api_server.tools.team_tools import TEAM_CREATE_TOOL, TEAM_DELETE_TOOL, TEAM_LIST_TOOL
from api_server.tools.synthetic_output_tool import SYNTHETIC_OUTPUT_TOOL
from api_server.tools.synthetic_output import TOOL_SYNTHETIC_OUTPUT
from api_server.tools.mcp_tools import (
    MCP_TOOL,
    MCP_AUTH_TOOL,
    LIST_MCP_RESOURCES_TOOL,
    READ_MCP_RESOURCE_TOOL,
)
from api_server.tools.schedule_cron_tool import SCHEDULE_CRON_TOOL
from api_server.tools.send_message_tool import SEND_MESSAGE_TOOL, BROADCAST_MESSAGE_TOOL
from api_server.tools.remote_trigger_tool import REMOTE_TRIGGER_TOOL
from api_server.tools.workflow_tool import WORKFLOW_EXECUTE_TOOL, WORKFLOW_LIST_TOOL
from api_server.tools.verify_plan_tool import VERIFY_PLAN_TOOL
from api_server.tools.snip_tool import SNIP_TOOL, SNIP_SAVE_TOOL, SNIP_LIST_TOOL
from api_server.tools.skill_tool import (
    SKILL_LIST_TOOL,
    SKILL_EXECUTE_TOOL,
    SKILL_SEARCH_TOOL,
    SKILL_INFO_TOOL,
)

# Claude Code Developer & System Tools
from api_server.tools.grep import GREP_TOOL
from api_server.tools.lsp import LSP_TOOL
from api_server.tools.agent import (
    AGENT_TOOL,
    SEND_MESSAGE_TO_AGENT_TOOL,
    TERMINATE_AGENT_TOOL,
    KILL_AGENT_TOOL,
    LIST_AGENTS_TOOL,
    GET_AGENT_STATUS_TOOL,
)
from api_server.tools.mcp_tool_registry import (
    LIST_MCP_SERVERS_TOOL,
    LIST_MCP_TOOLS_TOOL,
    MCP_TOOL as MCP_EXEC_TOOL,
    LIST_MCP_RESOURCES_TOOL as MCP_RESOURCES_LIST_TOOL,
    READ_MCP_RESOURCE_TOOL as MCP_RESOURCE_READ_TOOL,
)
from api_server.tools.repl import REPL_TOOL
from api_server.tools.bash import BASH_TOOL
from api_server.tools.powershell_tool import POWERSHELL_TOOL
from api_server.tools.tool_search import TOOL_SEARCH_TOOL as TOOL_SEARCH_NEW_TOOL
from api_server.tools.send_message import (
    SEND_MESSAGE_TOOL as SEND_MESSAGE_NEW_TOOL,
    BROADCAST_MESSAGE_TOOL as BROADCAST_MESSAGE_NEW_TOOL,
)


def register_all_tools() -> None:
    for tool in FILE_TOOLS:
        register_tool(tool)
    
    # shell_tool removed — no execute handler. Use BASH_TOOL instead.
    register_tool(web_fetch_tool)
    register_tool(web_search_tool)
    
    for tool in AGENT_TOOLS:
        register_tool(tool)
    
    register_tool(todo_write_tool)
    register_tool(TOOL_NOTEBOOK_EDIT)
    register_tool(TOOL_TODO_WRITE)
    register_tool(memory_read_tool)
    register_tool(memory_write_tool)
    register_tool(enter_plan_mode_tool)
    register_tool(exit_plan_mode_tool)
    register_tool(BRIEF_TOOL)
    register_tool(TOOL_BRIEF)
    register_tool(SLEEP_TOOL)
    register_tool(TOOL_SLEEP)
    register_tool(ASK_USER_TOOL)
    register_tool(TOOL_ASK_USER_QUESTION)
    register_tool(TOOL_CONFIG_GET)
    register_tool(TOOL_CONFIG_SET)
    register_tool(TOOL_CONFIG_GET)
    register_tool(TOOL_CONFIG_SET)
    
    register_tool(TaskCreateTool)
    register_tool(TaskGetTool)
    register_tool(TaskListTool)
    register_tool(TaskUpdateTool)
    register_tool(TaskStopTool)
    register_tool(TaskOutputTool)
    register_tool(WebSearchTool)
    register_tool(WebFetchTool)
    
    register_tool(ENTER_WORKTREE_TOOL)
    register_tool(EXIT_WORKTREE_TOOL)
    register_tool(LIST_WORKTREES_TOOL)
    
    register_tool(TOOL_SEARCH_TOOL)
    register_tool(TEAM_CREATE_TOOL)
    register_tool(TEAM_DELETE_TOOL)
    register_tool(TEAM_LIST_TOOL)
    register_tool(SYNTHETIC_OUTPUT_TOOL)
    register_tool(TOOL_SYNTHETIC_OUTPUT)
    register_tool(MCP_TOOL)
    register_tool(MCP_AUTH_TOOL)
    register_tool(LIST_MCP_RESOURCES_TOOL)
    register_tool(READ_MCP_RESOURCE_TOOL)
    register_tool(SEND_MESSAGE_TOOL)
    register_tool(BROADCAST_MESSAGE_TOOL)
    register_tool(REMOTE_TRIGGER_TOOL)
    register_tool(SCHEDULE_CRON_TOOL)
    register_tool(WORKFLOW_EXECUTE_TOOL)
    register_tool(WORKFLOW_LIST_TOOL)
    register_tool(VERIFY_PLAN_TOOL)
    register_tool(SNIP_TOOL)
    register_tool(SNIP_SAVE_TOOL)
    register_tool(SNIP_LIST_TOOL)
    register_tool(SKILL_LIST_TOOL)
    register_tool(SKILL_EXECUTE_TOOL)
    register_tool(SKILL_SEARCH_TOOL)
    register_tool(SKILL_INFO_TOOL)

    # Claude Code Developer & System Tools
    register_tool(GREP_TOOL)
    register_tool(LSP_TOOL)
    register_tool(AGENT_TOOL)
    register_tool(SEND_MESSAGE_TO_AGENT_TOOL)
    register_tool(TERMINATE_AGENT_TOOL)
    register_tool(KILL_AGENT_TOOL)
    register_tool(LIST_AGENTS_TOOL)
    register_tool(GET_AGENT_STATUS_TOOL)
    register_tool(LIST_MCP_SERVERS_TOOL)
    register_tool(LIST_MCP_TOOLS_TOOL)
    register_tool(MCP_EXEC_TOOL)
    register_tool(MCP_RESOURCES_LIST_TOOL)
    register_tool(MCP_RESOURCE_READ_TOOL)
    register_tool(REPL_TOOL)
    register_tool(BASH_TOOL)
    register_tool(POWERSHELL_TOOL)
    register_tool(TOOL_SEARCH_NEW_TOOL)
    register_tool(SEND_MESSAGE_NEW_TOOL)
    register_tool(BROADCAST_MESSAGE_NEW_TOOL)


__all__ = ["register_all_tools"]
