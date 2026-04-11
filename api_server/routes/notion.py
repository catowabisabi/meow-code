import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/notion", tags=["notion"])

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")


def _get_client():
    if not NOTION_API_KEY:
        raise HTTPException(status_code=500, detail="Notion API key not configured")
    try:
        from notion_client import NotionClient
        return NotionClient(NOTION_API_KEY)
    except ImportError:
        raise HTTPException(status_code=500, detail="Notion SDK not installed")


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    hasMore: bool = False
    nextCursor: Optional[str] = None


class PageResponse(BaseModel):
    page: Dict[str, Any]
    blocks: List[Dict[str, Any]]


class CreatePageRequest(BaseModel):
    parentId: str
    properties: Dict[str, Any] = {}
    children: List[Dict[str, Any]] = []


class QueryDatabaseRequest(BaseModel):
    filter: Optional[Dict[str, Any]] = None
    sorts: Optional[List[Dict[str, Any]]] = None


@router.get("/search")
async def search_notion(q: str = "", type: Optional[str] = None) -> dict:
    client = _get_client()
    try:
        filter = {"property": "object", "value": type} if type else None
        result = client.search(q, filter=filter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pages/{id}")
async def get_page(id: str) -> dict:
    client = _get_client()
    try:
        page = client.get_page(id)
        blocks = client.get_block_children(id)
        return {"page": page, "blocks": blocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages")
async def create_page(request: CreatePageRequest) -> dict:
    client = _get_client()
    try:
        result = client.create_page(
            parent_id=request.parentId,
            properties=request.properties,
            children=request.children,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases/{id}")
async def get_database(id: str) -> dict:
    client = _get_client()
    try:
        result = client.get_database(id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/databases/{id}/query")
async def query_database(id: str, request: QueryDatabaseRequest) -> dict:
    client = _get_client()
    try:
        results = client.query_database(
            database_id=id,
            filter=request.filter,
            sorts=request.sorts,
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
