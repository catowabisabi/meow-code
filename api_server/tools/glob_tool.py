"""Glob tool implementation - bridging gap with TypeScript GlobTool"""
import os
import fnmatch
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GlobMatch:
    path: str
    is_directory: bool
    size: Optional[int] = None


class GlobTool:
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
    
    async def glob(
        self,
        pattern: str,
        cwd: Optional[str] = None,
        max_results: int = 1000,
        include_hidden: bool = False
    ) -> List[GlobMatch]:
        base_dir = cwd or self.root_dir
        
        try:
            resolved_base = str(Path(base_dir).resolve())
        except (OSError, RuntimeError):
            return []
        
        matches = await self._glob_recursive(resolved_base, pattern, include_hidden)
        
        if len(matches) > max_results:
            matches = matches[:max_results]
        
        return matches
    
    async def _glob_recursive(
        self,
        base_dir: str,
        pattern: str,
        include_hidden: bool
    ) -> List[GlobMatch]:
        matches: List[GlobMatch] = []
        
        try:
            entries = os.listdir(base_dir)
        except (OSError, PermissionError):
            return matches
        
        for entry in entries:
            if not include_hidden and entry.startswith('.'):
                continue
            
            full_path = os.path.join(base_dir, entry)
            
            try:
                is_dir = os.path.isdir(full_path)
            except OSError:
                continue
            
            if fnmatch.fnmatch(entry, pattern):
                size = None
                if not is_dir:
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        pass
                
                matches.append(GlobMatch(
                    path=full_path,
                    is_directory=is_dir,
                    size=size
                ))
            
            if is_dir:
                sub_matches = await self._glob_recursive(full_path, pattern, include_hidden)
                matches.extend(sub_matches)
        
        return matches
    
    async def glob_single(
        self,
        pattern: str,
        cwd: Optional[str] = None
    ) -> Optional[GlobMatch]:
        matches = await self.glob(pattern, cwd, max_results=1)
        return matches[0] if matches else None


class GlobResult:
    def __init__(self, matches: List[GlobMatch]):
        self.matches = matches
    
    def model_dump(self) -> Dict[str, Any]:
        return {
            "matches": [
                {
                    "path": m.path,
                    "is_directory": m.is_directory,
                    "size": m.size
                }
                for m in self.matches
            ],
            "count": len(self.matches)
        }


async def execute_glob_tool(
    pattern: str,
    cwd: str = ".",
    max_results: int = 1000
) -> GlobResult:
    tool = GlobTool(cwd)
    matches = await tool.glob(pattern, cwd, max_results)
    return GlobResult(matches)


class GlobToolDefinition:
    name = "glob"
    description = "Find files by matching patterns"
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match (e.g., '**/*.ts', 'src/**/*.py')"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory to search in"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 1000
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Include hidden files (starting with .)",
                "default": False
            }
        },
        "required": ["pattern"]
    }
