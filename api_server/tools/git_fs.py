"""Git filesystem and session restore - bridging gaps"""
import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class GitFileContent:
    path: str
    content: bytes
    size: int
    is_binary: bool


class GitFilesystemReader:
    """
    Direct .git directory reading.
    
    TypeScript equivalent: gitFilesystem.ts
    Python gap: No direct .git reading - uses subprocess.
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.git_dir = self.repo_path / ".git"
    
    def exists(self) -> bool:
        return self.git_dir.exists() and self.git_dir.is_dir()
    
    def read_HEAD(self) -> Optional[str]:
        head_path = self.git_dir / "HEAD"
        if head_path.exists():
            return head_path.read_text().strip()
        return None
    
    def read_ref(self, ref: str) -> Optional[str]:
        ref_path = self.git_dir / ref
        if ref_path.exists():
            return ref_path.read_text().strip()
        return None
    
    def read_commit(self, sha: str) -> Optional[bytes]:
        obj_path = self.git_dir / "objects" / sha[:2] / sha[2:]
        if obj_path.exists():
            import zlib
            return zlib.decompress(obj_path.read_bytes())
        return None
    
    def list_worktrees(self) -> List[Dict[str, str]]:
        worktrees = []
        wt_dir = self.git_dir / "worktrees"
        
        if wt_dir.exists():
            for wt in wt_dir.iterdir():
                if wt.is_dir():
                    worktree = {
                        "path": wt.name,
                        "HEAD": "",
                        "branch": ""
                    }
                    
                    head_file = wt / "HEAD"
                    if head_file.exists():
                        worktree["HEAD"] = head_file.read_text().strip()
                    
                    refs_dir = wt / "refs"
                    if refs_dir.exists():
                        for ref_file in refs_dir.rglob("*"):
                            if ref_file.is_file():
                                worktree["branch"] = str(ref_file.parent / ref_file.name)
                                break
                    
                    worktrees.append(worktree)
        
        return worktrees


class SessionRestore:
    """
    Session resume with worktree/agent attribution.
    
    TypeScript equivalent: sessionRestore.ts
    Python gap: No session resume.
    """
    
    def __init__(self, storage_dir: str = "~/.claude/sessions"):
        self.storage_dir = Path(storage_dir).expanduser()
    
    def save_session_state(
        self,
        session_id: str,
        state: Dict[str, Any]
    ) -> bool:
        try:
            state_file = self.storage_dir / f"{session_id}_state.json"
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(state_file, "w") as f:
                json.dump(state, f)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            return False
    
    def restore_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            state_file = self.storage_dir / f"{session_id}_state.json"
            
            if not state_file.exists():
                return None
            
            import json
            with open(state_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to restore session state: {e}")
            return None
    
    def save_worktree_attribution(
        self,
        session_id: str,
        worktree_path: str,
        agent_id: str
    ) -> bool:
        try:
            attr_file = self.storage_dir / f"{session_id}_worktree_attr.json"
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            import json
            attr_file.write_text(json.dumps({
                "worktree_path": worktree_path,
                "agent_id": agent_id
            }))
            
            return True
        except Exception as e:
            logger.error(f"Failed to save worktree attribution: {e}")
            return False


_git_fs_readers: Dict[str, GitFilesystemReader] = {}


def get_git_filesystem_reader(repo_path: str) -> GitFilesystemReader:
    if repo_path not in _git_fs_readers:
        _git_fs_readers[repo_path] = GitFilesystemReader(repo_path)
    return _git_fs_readers[repo_path]
