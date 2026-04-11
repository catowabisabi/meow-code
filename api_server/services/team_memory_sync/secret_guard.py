"""
Secret protection for team memory files.

Checks if a file write/edit to a team memory path contains secrets.
Returns an error message if secrets are detected, or None if safe.

This is called from FileWriteTool and FileEditTool validateInput to
prevent the model from writing secrets into team memory files, which
would be synced to all repository collaborators.
"""

from typing import Optional, List

from .secret_scanner import scan_for_secrets, SecretMatch
from .types import SecretGuardConfig, SkippedSecretFile


class SecretGuard:
    def __init__(self, config: Optional[SecretGuardConfig] = None):
        self.config = config or SecretGuardConfig()

    def check_forbidden_secrets(self, content: str) -> List[SecretMatch]:
        if not self.config.enabled:
            return []
        return scan_for_secrets(content)

    def should_block_memory(self, content: str) -> bool:
        if not self.config.block_on_secret:
            return False
        return len(scan_for_secrets(content)) > 0

    def get_blocked_reasons(self, content: str) -> Optional[str]:
        matches = scan_for_secrets(content)
        if not matches:
            return None

        labels = ", ".join(m.label for m in matches)
        return (
            f"Content contains potential secrets ({labels}) and cannot be written to team memory. "
            "Team memory is shared with all repository collaborators. "
            "Remove the sensitive content and try again."
        )

    def filter_secret_files(
        self,
        files: List[SkippedSecretFile]
    ) -> List[SkippedSecretFile]:
        return [f for f in files if f.rule_id]


def check_team_mem_secrets(
    file_path: str,
    content: str,
    is_team_mem_path: bool,
) -> Optional[str]:
    if not is_team_mem_path:
        return None

    guard = SecretGuard()
    return guard.get_blocked_reasons(content)


def check_forbidden_secrets(content: str) -> List[SecretMatch]:
    return scan_for_secrets(content)


def should_block_memory(content: str) -> bool:
    guard = SecretGuard()
    return guard.should_block_memory(content)


def get_blocked_reasons(content: str) -> Optional[str]:
    guard = SecretGuard()
    return guard.get_blocked_reasons(content)
