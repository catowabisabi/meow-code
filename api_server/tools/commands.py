"""Init and branch commands - bridging gap with TypeScript commands/"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class InitConfig:
    project_name: str
    project_type: str
    git_init: bool = True
    install_dependencies: bool = True
    create_readme: bool = True
    template: Optional[str] = None


class InitCommand:
    """
    Multi-phase interactive wizard flow.
    
    TypeScript equivalent: commands/init.ts
    Python gap: Basic file creation - missing interactive wizard.
    """
    
    def __init__(self):
        self.config: Optional[InitConfig] = None
        self.current_step = 0
        self.steps = [
            "welcome",
            "project_type",
            "project_name",
            "options",
            "confirmation",
            "creation"
        ]
    
    async def run_interactive(self) -> bool:
        self.current_step = 0
        
        for step in self.steps:
            if step == "welcome":
                if not await self._step_welcome():
                    return False
            elif step == "project_type":
                if not await self._step_project_type():
                    return False
            elif step == "project_name":
                if not await self._step_project_name():
                    return False
            elif step == "options":
                await self._step_options()
            elif step == "confirmation":
                if not await self._step_confirmation():
                    return False
            elif step == "creation":
                await self._step_creation()
        
        return True
    
    async def _step_welcome(self) -> bool:
        print("Welcome to Claude Code!")
        print("This wizard will help you set up a new project.")
        return True
    
    async def _step_project_type(self) -> bool:
        project_types = ["python", "javascript", "typescript", "rust", "go", "java", "other"]
        print("\nSelect project type:")
        for i, pt in enumerate(project_types):
            print(f"  {i+1}. {pt}")
        return True
    
    async def _step_project_name(self) -> bool:
        print("\nEnter project name:")
        return True
    
    async def _step_options(self) -> None:
        print("\nAdditional options:")
        print("  [x] Initialize git repository")
        print("  [x] Install dependencies")
        print("  [x] Create README.md")
    
    async def _step_confirmation(self) -> bool:
        print("\nReady to create project. Proceed? [Y/n]")
        return True
    
    async def _step_creation(self) -> None:
        if not self.config:
            return
        
        project_path = Path.cwd() / self.config.project_name
        project_path.mkdir(exist_ok=True)
        
        if self.config.git_init:
            subprocess.run(["git", "init"], cwd=project_path, check=False)
        
        if self.config.create_readme:
            readme_path = project_path / "README.md"
            readme_path.write_text(f"# {self.config.project_name}\n")
        
        print(f"\nProject created at {project_path}")


class BranchCommand:
    """
    Git branch/fork management.
    
    TypeScript equivalent: commands/branch/branch.ts
    Python gap: No branch/fork command.
    """
    
    def __init__(self):
        self.worktrees: Dict[str, str] = {}
    
    async def create_worktree(
        self,
        branch_name: str,
        path: Optional[str] = None,
        create_branch: bool = True
    ) -> bool:
        if not path:
            path = f".claude/worktrees/{branch_name}"
        
        try:
            args = ["git", "worktree", "add"]
            
            if create_branch:
                args.extend(["-b", branch_name])
            
            args.append(path)
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.worktrees[branch_name] = path
                return True
            
            logger.error(f"Failed to create worktree: {result.stderr}")
            return False
        
        except Exception as e:
            logger.error(f"Worktree creation error: {e}")
            return False
    
    async def list_worktrees(self) -> List[Dict[str, str]]:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True
        )
        
        worktrees = []
        current = {}
        
        for line in result.stdout.split("\n"):
            if not line:
                continue
            
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("branch "):
                current["branch"] = line[8:]
        
        if current:
            worktrees.append(current)
        
        return worktrees
    
    async def remove_worktree(self, path: str, force: bool = False) -> bool:
        args = ["git", "worktree", "remove", path]
        
        if force:
            args.append("--force")
        
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Worktree removal error: {e}")
            return False
    
    async def prune_worktrees(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "worktree", "prune"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Worktree prune error: {e}")
            return False


_init_command: Optional[InitCommand] = None
_branch_command: Optional[BranchCommand] = None


def get_init_command() -> InitCommand:
    global _init_command
    if _init_command is None:
        _init_command = InitCommand()
    return _init_command


def get_branch_command() -> BranchCommand:
    global _branch_command
    if _branch_command is None:
        _branch_command = BranchCommand()
    return _branch_command
