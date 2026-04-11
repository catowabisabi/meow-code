from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommandCategory(Enum):
    SEARCH = "search"
    READ = "read"
    WRITE = "write"
    MODIFY = "modify"
    EXECUTE = "execute"
    UNKNOWN = "unknown"


@dataclass
class PowerShellResult:
    output: str
    is_error: bool = False
    exit_code: int = 0
    category: CommandCategory = CommandCategory.UNKNOWN
    is_read_only: bool = False
    metadata: dict = field(default_factory=dict)