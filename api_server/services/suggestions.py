import asyncio
import re
from dataclasses import dataclass
from typing import Callable, Awaitable


@dataclass
class SuggestionConfig:
    max_suggestions: int = 10
    min_score: float = 0.5


@dataclass
class Suggestion:
    text: str
    score: float
    source: str


async def get_shell_suggestions(
    partial: str,
    cwd: str,
    history: list[str] | None = None,
) -> list[Suggestion]:
    return []


async def get_file_suggestions(
    partial: str,
    cwd: str,
    max_depth: int = 3,
) -> list[Suggestion]:
    return []


async def get_command_suggestions(
    partial: str,
    cwd: str,
) -> list[Suggestion]:
    return []


async def get_directory_suggestions(
    partial: str,
    cwd: str,
) -> list[Suggestion]:
    return []
