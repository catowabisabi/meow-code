"""
Skill Management Service.
Skills are stored as .md files in the skills/ directory.
"""
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class Skill(BaseModel):
    name: str
    description: str = ""
    triggers: list[str] = []
    enabled: bool = True
    isDefault: bool = True


class SkillDetail(Skill):
    prompt: str = ""


def _get_skills_dir() -> Path:
    return Path(__file__).parent.parent.parent / "skills"


def _parse_skill_md(file_path: Path) -> tuple[str, str, list[str]]:
    content = file_path.read_text(encoding="utf-8")

    lines = content.strip().split("\n")
    name = file_path.stem

    description = ""
    triggers: list[str] = []

    for line in lines[:5]:
        line = line.strip()
        if line.startswith("# "):
            name = line[2:].strip()
            break
        elif line.startswith("## "):
            name = line[3:].strip()
            break

    desc_pattern = re.compile(r"(?:Description|Desc):\s*(.+)", re.IGNORECASE)
    trigger_pattern = re.compile(r"(?:Trigger|Triggers):\s*(.+)", re.IGNORECASE)

    for line in lines[5:20]:
        desc_match = desc_pattern.search(line)
        if desc_match:
            description = desc_match.group(1).strip()

        trigger_match = trigger_pattern.search(line)
        if trigger_match:
            trigger_str = trigger_match.group(1).strip()
            triggers = [t.strip() for t in trigger_str.split(",")]

    return name, description, triggers


class SkillService:
    @staticmethod
    def load_skills() -> list[Skill]:
        skills: list[Skill] = []
        skills_dir = _get_skills_dir()

        if not skills_dir.exists():
            return skills

        for file_path in skills_dir.glob("*.md"):
            if file_path.stem.upper().startswith(("SKILLS_", "UPDATE_")):
                continue

            name, description, triggers = _parse_skill_md(file_path)
            skills.append(
                Skill(
                    name=name,
                    description=description,
                    triggers=triggers,
                    enabled=True,
                    isDefault=True,
                )
            )

        return skills

    @staticmethod
    def get_skill(name: str) -> Optional[SkillDetail]:
        skills_dir = _get_skills_dir()

        if not skills_dir.exists():
            return None

        for file_path in skills_dir.glob("*.md"):
            skill_name, description, triggers = _parse_skill_md(file_path)
            if skill_name.lower() == name.lower():
                content = file_path.read_text(encoding="utf-8")
                return SkillDetail(
                    name=skill_name,
                    description=description,
                    triggers=triggers,
                    enabled=True,
                    isDefault=True,
                    prompt=content,
                )

        return None

    @staticmethod
    def execute_skill(skill: SkillDetail, context: dict) -> dict[str, Any]:
        return {
            "skillName": skill.name,
            "systemPrompt": skill.prompt,
            "success": True,
            "error": None,
        }
