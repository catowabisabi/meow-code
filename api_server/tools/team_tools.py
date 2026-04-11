"""Team tools - create and manage teams of agents."""
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import ToolDef, ToolContext, ToolResult


TEAMS_DIR = Path.home() / ".claude" / "teams"
TEAMS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TeamMember:
    name: str
    agent_id: str
    role: str = "member"


@dataclass 
class Team:
    name: str
    members: List[TeamMember]
    created_at: int


def load_team(name: str) -> Optional[Team]:
    team_file = TEAMS_DIR / f"{name}.json"
    if not team_file.exists():
        return None
    try:
        data = json.loads(team_file.read_text())
        return Team(
            name=data["name"],
            members=[TeamMember(**m) for m in data.get("members", [])],
            created_at=data.get("created_at", 0),
        )
    except:
        return None


def save_team(team: Team) -> None:
    team_file = TEAMS_DIR / f"{team.name}.json"
    data = {
        "name": team.name,
        "members": [vars(m) for m in team.members],
        "created_at": team.created_at,
    }
    team_file.write_text(json.dumps(data, indent=2))


from dataclasses import dataclass


async def _team_create(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    name = args.get('name')
    members = args.get('members', [])
    
    if not name:
        return ToolResult(tool_call_id=tool_call_id, output="name is required", is_error=True)
    
    team = Team(
        name=name,
        members=[TeamMember(**m) for m in members],
        created_at=int(uuid.uuid1().time),
    )
    
    save_team(team)
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output=f"Created team '{name}' with {len(members)} members",
        is_error=False,
    )


async def _team_delete(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    name = args.get('name')
    
    if not name:
        return ToolResult(tool_call_id=tool_call_id, output="name is required", is_error=True)
    
    team_file = TEAMS_DIR / f"{name}.json"
    if team_file.exists():
        team_file.unlink()
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Deleted team '{name}'",
            is_error=False,
        )
    else:
        return ToolResult(
            tool_call_id=tool_call_id,
            output=f"Team '{name}' not found",
            is_error=True,
        )


async def _team_list(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '') or ""
    
    teams = list(TEAMS_DIR.glob("*.json"))
    
    if not teams:
        return ToolResult(
            tool_call_id=tool_call_id,
            output="No teams found",
            is_error=False,
        )
    
    lines = []
    for team_file in teams:
        name = team_file.stem
        data = json.loads(team_file.read_text())
        member_count = len(data.get("members", []))
        lines.append(f"- {name}: {member_count} members")
    
    return ToolResult(
        tool_call_id=tool_call_id,
        output="\n".join(lines),
        is_error=False,
    )


TEAM_CREATE_TOOL = ToolDef(
    name="team_create",
    description="Create a team of agents.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Team name"},
            "members": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
                "description": "Team members",
            },
        },
        "required": ["name"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=_team_create,
)


TEAM_DELETE_TOOL = ToolDef(
    name="team_delete",
    description="Delete a team.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Team name"},
        },
        "required": ["name"],
    },
    is_read_only=False,
    risk_level="high",
    execute=_team_delete,
)


TEAM_LIST_TOOL = ToolDef(
    name="team_list",
    description="List all teams.",
    input_schema={
        "type": "object",
        "properties": {},
    },
    is_read_only=True,
    risk_level="low",
    execute=_team_list,
)


__all__ = ["TEAM_CREATE_TOOL", "TEAM_DELETE_TOOL", "TEAM_LIST_TOOL"]
