"""Skill management and invocation tool.

Based on TypeScript SkillTool implementation.
Loads and executes skills from the skill registry.
"""
from .types import ToolDef, ToolContext, ToolResult
from api_server.services.skills.registry import (
    get_skill,
    list_skills,
    search_skills,
    list_skills_by_category,
    list_skills_by_tag,
    SkillContext,
)
from api_server.services.skills.executor import execute_skill as exec_skill


async def skill_list_impl(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    category = args.get("category")
    tag = args.get("tag")
    enabled_only = args.get("enabled_only", True)

    if category:
        skills = list_skills_by_category(category)
    elif tag:
        skills = list_skills_by_tag(tag)
    else:
        skills = list_skills()

    if enabled_only:
        skills = [s for s in skills if s.is_enabled]

    if not skills:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No skills found matching the criteria",
            is_error=False,
        )

    lines = [f"Available skills ({len(skills)}):"]
    for skill in skills:
        lines.append(f"  - {skill.name}: {skill.description}")

    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(lines),
        is_error=False,
    )


async def skill_execute_impl(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    skill_name = args.get("skill_name", "")
    input_text = args.get("input_text", "")

    if not skill_name:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'skill_name' field is required",
            is_error=True,
        )

    skill = get_skill(skill_name)
    if not skill:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Skill '{skill_name}' not found",
            is_error=True,
        )

    if not skill.is_enabled:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Skill '{skill_name}' is disabled",
            is_error=True,
        )

    context = SkillContext(
        input_text=input_text,
        context={"cwd": ctx.cwd} if ctx.cwd else None,
    )

    result = exec_skill(skill_name, context)

    if result.success:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=result.output or result.system_prompt,
            is_error=False,
        )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error executing skill: {result.error}",
            is_error=True,
        )


async def skill_search_impl(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    query = args.get("query", "")

    if not query:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'query' field is required",
            is_error=True,
        )

    results = search_skills(query)

    if not results:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"No skills found matching '{query}'",
            is_error=False,
        )

    lines = [f"Skills matching '{query}' ({len(results)}):"]
    for skill in results:
        lines.append(f"  - {skill.name}: {skill.description}")

    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(lines),
        is_error=False,
    )


async def skill_info_impl(args: dict, ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    skill_name = args.get("skill_name", "")

    if not skill_name:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="Error: 'skill_name' field is required",
            is_error=True,
        )

    skill = get_skill(skill_name)
    if not skill:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Error: Skill '{skill_name}' not found",
            is_error=True,
        )

    info = [
        f"Skill: {skill.name}",
        f"Description: {skill.description}",
        f"Category: {skill.category}",
        f"Version: {skill.version}",
        f"Enabled: {skill.is_enabled}",
        f"Builtin: {skill.is_builtin}",
        f"Tags: {', '.join(skill.tags) if skill.tags else 'none'}",
        f"Triggers: {', '.join(skill.triggers) if skill.triggers else 'none'}",
        f"Author: {skill.author or 'unknown'}",
    ]

    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(info),
        is_error=False,
    )


SKILL_LIST_TOOL = ToolDef(
    name="skill_list",
    description="List all available skills, optionally filtered by category or tag",
    input_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter skills by category",
            },
            "tag": {
                "type": "string",
                "description": "Filter skills by tag",
            },
            "enabled_only": {
                "type": "boolean",
                "description": "Only show enabled skills (default: true)",
            },
        },
    },
    is_read_only=True,
    risk_level="low",
    execute=skill_list_impl,
)


SKILL_EXECUTE_TOOL = ToolDef(
    name="skill_execute",
    description="Execute a specific skill by name",
    input_schema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The name of the skill to execute",
            },
            "input_text": {
                "type": "string",
                "description": "Input text or arguments for the skill",
            },
        },
        "required": ["skill_name"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=skill_execute_impl,
)


SKILL_SEARCH_TOOL = ToolDef(
    name="skill_search",
    description="Search for skills by name, description, tags, or triggers",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to match against skill names, descriptions, tags, and triggers",
            },
        },
        "required": ["query"],
    },
    is_read_only=True,
    risk_level="low",
    execute=skill_search_impl,
)


SKILL_INFO_TOOL = ToolDef(
    name="skill_info",
    description="Get detailed information about a specific skill",
    input_schema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The name of the skill to get info about",
            },
        },
        "required": ["skill_name"],
    },
    is_read_only=True,
    risk_level="low",
    execute=skill_info_impl,
)


__all__ = [
    "SKILL_LIST_TOOL",
    "SKILL_EXECUTE_TOOL",
    "SKILL_SEARCH_TOOL",
    "SKILL_INFO_TOOL",
]