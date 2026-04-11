"""
REST API for skill management.

Skills are stored as .md files with YAML frontmatter in skills/ directories.
Compatible with Claude Code's skill format.
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_server.services.skills.loader import SkillLoader
from api_server.services.skills.registry import (
    SkillDefinition,
    SkillContext,
    get_registry,
    register_skill,
)
from api_server.services.skills.executor import execute_skill
from api_server.services.skills.builtin_skills import register_builtin_skills

router = APIRouter(prefix="/skills", tags=["skills"])

register_builtin_skills()

SKILLS_DIRS = [
    Path(__file__).parent.parent.parent / "skills",
    Path.home() / ".claude" / "skills",
]


class Skill(BaseModel):
    name: str
    description: str = ""
    allowed_tools: list[str] = []
    argument_hint: str | None = None
    when_to_use: str | None = None
    user_invocable: bool = True
    model: str | None = None
    effort: str | None = None
    context: str | None = None
    agent: str | None = None
    paths: list[str] = []
    version: str | None = None
    shell: str | None = None
    tags: list[str] = []
    category: str = "general"
    is_builtin: bool = False
    is_enabled: bool = True
    triggers: list[str] = []
    source: str = "unknown"


class SkillDetail(Skill):
    prompt: str = ""
    skill_dir: str | None = None


class ListSkillsResponse(BaseModel):
    skills: list[Skill]
    count: int


class ExecuteSkillRequest(BaseModel):
    name: str
    args: str | None = None
    cwd: str | None = None
    context: dict[str, Any] | None = None


class ExecuteSkillResponse(BaseModel):
    skillName: str
    systemPrompt: str
    success: bool
    error: str | None = None
    output: str | None = None


class LoadSkillsRequest(BaseModel):
    path: str | None = None


class LoadSkillsResponse(BaseModel):
    ok: bool
    loaded_count: int
    skill_names: list[str]


class RegisterSkillRequest(BaseModel):
    name: str
    description: str = ""
    prompt: str
    allowed_tools: list[str] = []
    argument_hint: str | None = None
    when_to_use: str | None = None
    user_invocable: bool = True
    model: str | None = None
    effort: str | None = None
    context: str | None = None
    agent: str | None = None
    paths: list[str] = []
    version: str | None = None
    shell: str | None = None
    tags: list[str] = []
    category: str = "general"
    triggers: list[str] = []
    is_builtin: bool = False
    is_enabled: bool = True


class ErrorResponse(BaseModel):
    error: str


_loader: SkillLoader | None = None


def get_loader() -> SkillLoader:
    global _loader
    if _loader is None:
        _loader = SkillLoader()
        for skills_dir in SKILLS_DIRS:
            if skills_dir.exists():
                _loader.load_from_dir(skills_dir)
    return _loader


def _skill_to_model(skill_def: SkillDefinition) -> Skill:
    return Skill(
        name=skill_def.name,
        description=skill_def.description,
        allowed_tools=skill_def.allowed_tools,
        argument_hint=skill_def.argument_hint,
        when_to_use=skill_def.when_to_use,
        user_invocable=skill_def.user_invocable,
        model=skill_def.model,
        effort=skill_def.effort,
        context=skill_def.context,
        agent=skill_def.agent,
        paths=skill_def.paths,
        version=skill_def.version,
        shell=skill_def.shell,
        tags=skill_def.tags,
        category=skill_def.category,
        is_builtin=skill_def.is_builtin,
        is_enabled=skill_def.is_enabled,
        triggers=skill_def.triggers,
        source=skill_def.source,
    )


def _skill_to_detail(skill_def: SkillDefinition) -> SkillDetail:
    return SkillDetail(
        name=skill_def.name,
        description=skill_def.description,
        allowed_tools=skill_def.allowed_tools,
        argument_hint=skill_def.argument_hint,
        when_to_use=skill_def.when_to_use,
        user_invocable=skill_def.user_invocable,
        model=skill_def.model,
        effort=skill_def.effort,
        context=skill_def.context,
        agent=skill_def.agent,
        paths=skill_def.paths,
        version=skill_def.version,
        shell=skill_def.shell,
        tags=skill_def.tags,
        category=skill_def.category,
        is_builtin=skill_def.is_builtin,
        is_enabled=skill_def.is_enabled,
        triggers=skill_def.triggers,
        source=skill_def.source,
        prompt=skill_def.prompt,
        skill_dir=str(skill_def.skill_dir) if skill_def.skill_dir else None,
    )


@router.get("", response_model=ListSkillsResponse)
async def list_skills() -> ListSkillsResponse:
    registry = get_registry()
    all_skills = registry.list_all()
    
    if not all_skills:
        loader = get_loader()
        for parsed in loader.list_skills():
            skill_def = SkillDefinition(
                name=parsed.name,
                description=parsed.description,
                prompt=parsed.content,
                allowed_tools=parsed.frontmatter.allowed_tools,
                argument_hint=parsed.frontmatter.argument_hint,
                when_to_use=parsed.frontmatter.when_to_use,
                user_invocable=parsed.frontmatter.user_invocable,
                model=parsed.frontmatter.model,
                effort=parsed.frontmatter.effort,
                context=parsed.frontmatter.context,
                agent=parsed.frontmatter.agent,
                paths=parsed.frontmatter.paths,
                version=parsed.frontmatter.version,
                shell=parsed.frontmatter.shell,
                tags=parsed.frontmatter.tags,
                category=parsed.frontmatter.category,
                is_builtin=True,
                source=str(parsed.source_path),
                skill_dir=parsed.skill_dir,
            )
            register_skill(skill_def)
        
        all_skills = registry.list_all()
    
    skills = [_skill_to_model(s) for s in all_skills]
    return ListSkillsResponse(skills=skills, count=len(skills))


@router.get("/{name}", response_model=SkillDetail)
async def get_skill_by_name(name: str) -> SkillDetail:
    registry = get_registry()
    skill = registry.get(name)
    
    if not skill:
        loader = get_loader()
        parsed = loader.get_skill(name)
        if parsed:
            skill_def = SkillDefinition(
                name=parsed.name,
                description=parsed.description,
                prompt=parsed.content,
                allowed_tools=parsed.frontmatter.allowed_tools,
                argument_hint=parsed.frontmatter.argument_hint,
                when_to_use=parsed.frontmatter.when_to_use,
                user_invocable=parsed.frontmatter.user_invocable,
                model=parsed.frontmatter.model,
                effort=parsed.frontmatter.effort,
                context=parsed.frontmatter.context,
                agent=parsed.frontmatter.agent,
                paths=parsed.frontmatter.paths,
                version=parsed.frontmatter.version,
                shell=parsed.frontmatter.shell,
                tags=parsed.frontmatter.tags,
                category=parsed.frontmatter.category,
                is_builtin=True,
                source=str(parsed.source_path),
                skill_dir=parsed.skill_dir,
            )
            register_skill(skill_def)
            skill = skill_def
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    
    return _skill_to_detail(skill)


@router.post("/execute", response_model=ExecuteSkillResponse)
async def execute_skill_endpoint(request: ExecuteSkillRequest) -> ExecuteSkillResponse:
    if not request.name:
        raise HTTPException(status_code=400, detail="name is required")
    
    skill = get_registry().get(request.name)
    if not skill:
        parsed = get_loader().get_skill(request.name)
        if parsed:
            skill_def = SkillDefinition(
                name=parsed.name,
                description=parsed.description,
                prompt=parsed.content,
                allowed_tools=parsed.frontmatter.allowed_tools,
                argument_hint=parsed.frontmatter.argument_hint,
                when_to_use=parsed.frontmatter.when_to_use,
                user_invocable=parsed.frontmatter.user_invocable,
                model=parsed.frontmatter.model,
                effort=parsed.frontmatter.effort,
                context=parsed.frontmatter.context,
                agent=parsed.frontmatter.agent,
                paths=parsed.frontmatter.paths,
                version=parsed.frontmatter.version,
                shell=parsed.frontmatter.shell,
                tags=parsed.frontmatter.tags,
                category=parsed.frontmatter.category,
                is_builtin=True,
                source=str(parsed.source_path),
                skill_dir=parsed.skill_dir,
            )
            register_skill(skill_def)
            skill = skill_def
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{request.name}' not found")
    
    context = SkillContext(
        input_text=request.args or "",
        cwd=request.cwd or "",
        context=request.context,
    )
    
    result = execute_skill(request.name, context)
    
    return ExecuteSkillResponse(
        skillName=result.skill_name,
        systemPrompt=result.system_prompt,
        success=result.success,
        error=result.error,
        output=result.output,
    )


@router.post("/load", response_model=LoadSkillsResponse)
async def load_skills_endpoint(request: LoadSkillsRequest) -> LoadSkillsResponse:
    global _loader
    
    if request.path:
        skills_path = Path(request.path)
    else:
        skills_path = Path.home() / ".claude" / "skills"
    
    if not skills_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {skills_path}")
    
    loader = get_loader()
    parsed_skills = loader.load_from_dir(skills_path)
    
    for parsed in parsed_skills:
        skill_def = SkillDefinition(
            name=parsed.name,
            description=parsed.description,
            prompt=parsed.content,
            allowed_tools=parsed.frontmatter.allowed_tools,
            argument_hint=parsed.frontmatter.argument_hint,
            when_to_use=parsed.frontmatter.when_to_use,
            user_invocable=parsed.frontmatter.user_invocable,
            model=parsed.frontmatter.model,
            effort=parsed.frontmatter.effort,
            context=parsed.frontmatter.context,
            agent=parsed.frontmatter.agent,
            paths=parsed.frontmatter.paths,
            version=parsed.frontmatter.version,
            shell=parsed.frontmatter.shell,
            tags=parsed.frontmatter.tags,
            category=parsed.frontmatter.category,
            is_builtin=False,
            source=str(parsed.source_path),
            skill_dir=parsed.skill_dir,
        )
        register_skill(skill_def)
    
    return LoadSkillsResponse(
        ok=True,
        loaded_count=len(parsed_skills),
        skill_names=[s.name for s in parsed_skills],
    )


@router.post("/register", response_model=SkillDetail)
async def register_skill_endpoint(request: RegisterSkillRequest) -> SkillDetail:
    existing = get_registry().get(request.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{request.name}' already exists")
    
    skill_def = SkillDefinition(
        name=request.name,
        description=request.description,
        prompt=request.prompt,
        allowed_tools=request.allowed_tools,
        argument_hint=request.argument_hint,
        when_to_use=request.when_to_use,
        user_invocable=request.user_invocable,
        model=request.model,
        effort=request.effort,
        context=request.context,
        agent=request.agent,
        paths=request.paths,
        version=request.version,
        shell=request.shell,
        tags=request.tags,
        category=request.category,
        triggers=request.triggers,
        is_builtin=request.is_builtin,
        is_enabled=request.is_enabled,
        source="api",
    )
    register_skill(skill_def)
    
    return _skill_to_detail(skill_def)
