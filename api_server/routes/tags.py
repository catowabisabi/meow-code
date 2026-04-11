"""
FastAPI routes for session tagging.
"""
import json
import re
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["tags"])

# In-memory storage
_session_tags: Dict[str, dict] = {}

# Persistence
TAGS_FILE = Path.home() / ".claude" / "session_tags.json"

# Validation pattern: alphanumeric, hyphens, underscores only
TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_TAG_LENGTH = 50


class TagRequest(BaseModel):
    tag: str  # tag name without # prefix


class TagResponse(BaseModel):
    session_id: str
    tag: Optional[str]  # None if no tag set
    updated_at: Optional[float]


def _load_tags() -> None:
    """Load tags from JSON file into memory."""
    global _session_tags
    if TAGS_FILE.exists():
        try:
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _session_tags = data
        except (json.JSONDecodeError, IOError):
            _session_tags = {}


def _save_tags() -> None:
    """Persist in-memory tags to JSON file."""
    TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_session_tags, f, ensure_ascii=False, indent=2)


def _normalize_tag(tag: str) -> str:
    """Normalize tag: lowercase, trim whitespace."""
    return tag.strip().lower()


def _validate_tag(tag: str) -> str:
    """Validate and normalize tag. Raises HTTPException if invalid."""
    normalized = _normalize_tag(tag)
    if not normalized:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")
    if len(normalized) > MAX_TAG_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Tag name must be {MAX_TAG_LENGTH} characters or less",
        )
    if not TAG_PATTERN.match(normalized):
        raise HTTPException(
            status_code=400,
            detail="Tag names can only contain letters, numbers, hyphens, and underscores",
        )
    return normalized


# Initialize from file on module load
_load_tags()


@router.get("/{session_id}/tag", response_model=TagResponse)
async def get_session_tag(session_id: str) -> TagResponse:
    """Get the tag for a session."""
    tag_data = _session_tags.get(session_id)
    if tag_data:
        return TagResponse(
            session_id=session_id,
            tag=tag_data.get("tag"),
            updated_at=tag_data.get("updated_at"),
        )
    return TagResponse(session_id=session_id, tag=None, updated_at=None)


@router.post("/{session_id}/tag", response_model=TagResponse)
async def set_session_tag(session_id: str, tag_req: TagRequest) -> TagResponse:
    """Set or update the tag for a session."""
    normalized_tag = _validate_tag(tag_req.tag)
    now = time.time()
    _session_tags[session_id] = {"tag": normalized_tag, "updated_at": now}
    _save_tags()
    return TagResponse(session_id=session_id, tag=normalized_tag, updated_at=now)


@router.delete("/{session_id}/tag")
async def delete_session_tag(session_id: str) -> Dict:
    """Remove the tag from a session."""
    if session_id in _session_tags:
        del _session_tags[session_id]
        _save_tags()
    return {"ok": True}