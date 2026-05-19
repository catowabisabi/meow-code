import subprocess
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class GitStatus:
    branch: str
    staged: List[str]
    modified: List[str]
    untracked: List[str]
    conflicted: List[str]


@dataclass
class GitCommit:
    hash: str
    message: str
    author: str
    date: str


@dataclass
class GitDiff:
    file: str
    status: str
    additions: int
    deletions: int
    hunks: List[Dict[str, Any]]


class GitService:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _run(self, args: List[str], cwd: Optional[str] = None) -> str:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or self.repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        return result.stdout

    def get_status(self) -> GitStatus:
        output = self._run(["status", "--porcelain"])
        staged = []
        modified = []
        untracked = []
        conflicted = []
        branch = self._run(["branch", "--show-current"]).strip()

        for line in output.splitlines():
            if not line:
                continue
            index_status = line[0]
            worktree_status = line[1]
            file_path = line[3:]

            if index_status == "?" and worktree_status == "?":
                untracked.append(file_path)
            elif index_status == "U" or worktree_status == "U":
                conflicted.append(file_path)
            elif index_status != " ":
                staged.append(file_path)
            elif worktree_status != " ":
                modified.append(file_path)

        return GitStatus(
            branch=branch,
            staged=staged,
            modified=modified,
            untracked=untracked,
            conflicted=conflicted,
        )

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> List[GitDiff]:
        args = ["diff", "--numstat"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append("--")
            args.append(file_path)

        output = self._run(args)
        diffs = []

        for line in output.splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            file = parts[2] if len(parts) > 2 else parts[0]
            additions = int(parts[0]) if parts[0] != "-" else 0
            deletions = int(parts[1]) if parts[1] != "-" else 0

            hunks_output = self._run(["diff", "--unified=3", "--", file])
            hunks = []
            current_hunk = None

            for hunk_line in hunks_output.splitlines():
                if hunk_line.startswith("@@"):
                    if current_hunk:
                        hunks.append(current_hunk)
                    info = hunk_line[3:].split(" @@")[0]
                    current_hunk = {"lines": [], "additions": 0, "deletions": 0}
                    start = info.split(" ")[0]
                    if start.startswith("+"):
                        current_hunk["start_line"] = int(start[1:])
                    elif start.startswith("-"):
                        current_hunk["start_line"] = int(start[1:])
                    else:
                        current_hunk["start_line"] = int(start)
                elif current_hunk is not None:
                    current_hunk["lines"].append(hunk_line)
                    if hunk_line.startswith("+"):
                        current_hunk["additions"] += 1
                    elif hunk_line.startswith("-"):
                        current_hunk["deletions"] += 1

            if current_hunk:
                hunks.append(current_hunk)

            status = "modified"
            if file in self.get_status().staged:
                status = "staged"
            elif file in self.get_status().untracked:
                status = "untracked"

            diffs.append(GitDiff(
                file=file,
                status=status,
                additions=additions,
                deletions=deletions,
                hunks=hunks or [],
            ))

        return diffs

    def get_log(self, max_count: int = 50) -> List[GitCommit]:
        output = self._run(["log", f"-{max_count}", "--pretty=format:%H|%s|%an|%ad", "--date=iso"])
        commits = []

        for line in output.splitlines():
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 4:
                continue

            commits.append(GitCommit(
                hash=parts[0],
                message=parts[1],
                author=parts[2],
                date=parts[3],
            ))

        return commits

    def stage(self, files: List[str]) -> None:
        if not files:
            return
        self._run(["add", "--"] + files)

    def unstage(self, files: List[str]) -> None:
        if not files:
            return
        self._run(["reset", "HEAD", "--"] + files)

    def commit(self, message: str) -> str:
        self._run(["commit", "-m", message])
        return self.get_log(1)[0].hash

    def get_branches(self) -> Dict[str, List[str]]:
        output = self._run(["branch", "-a"])
        current = self._run(["branch", "--show-current"]).strip()

        branches = {"current": current, "local": [], "remote": []}

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("*"):
                line = line[2:]
            if line.startswith("remotes/"):
                branches["remote"].append(line.replace("remotes/", ""))
            else:
                branches["local"].append(line)

        return branches

    def checkout(self, branch: str) -> None:
        self._run(["checkout", branch])

    def create_branch(self, name: str, from_branch: Optional[str] = None) -> None:
        args = ["checkout", "-b", name]
        if from_branch:
            args.append(from_branch)
        self._run(args)

    def merge(self, branch: str) -> None:
        self._run(["merge", branch])

    def get_file_content(self, file_path: str, ref: Optional[str] = None) -> str:
        args = ["show"]
        if ref:
            args.append(f"{ref}:{file_path}")
        else:
            args.append(f"HEAD:{file_path}")
        try:
            return self._run(args)
        except RuntimeError:
            return ""