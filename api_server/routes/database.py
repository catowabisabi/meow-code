import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import aiosqlite
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/databases", tags=["databases"])

DB_DIR = Path.home() / ".claude" / "databases"


def _ensure_dir() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)


def _safe_db_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    if not safe or safe.startswith("_"):
        raise HTTPException(status_code=400, detail="Invalid database name")
    return safe


def _get_db_path(name: str) -> Path:
    safe_name = _safe_db_name(name)
    return DB_DIR / f"{safe_name}.db"


class DatabaseInfo(BaseModel):
    name: str
    size: int
    sizeFormatted: str
    modified: str


class TableInfo(BaseModel):
    name: str
    columns: List[dict]
    rowCount: int


class QueryRequest(BaseModel):
    sql: str
    params: Optional[List[Any]] = None


class CreateDatabaseRequest(BaseModel):
    name: str


@router.get("")
async def list_databases() -> dict:
    _ensure_dir()
    try:
        files = [f for f in DB_DIR.iterdir() if f.suffix == ".db"]
        databases = []
        for f in files:
            stat = f.stat()
            databases.append(
                DatabaseInfo(
                    name=f.stem,
                    size=stat.st_size,
                    sizeFormatted=f"{(stat.st_size / 1024):.1f} KB",
                    modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                )
            )
        return {"databases": [db.model_dump() for db in databases]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/tables")
async def list_tables(name: str) -> dict:
    db_path = _get_db_path(name)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        rows = await cursor.fetchall()
        tables = []
        for row in rows:
            table_name = row["name"]
            pragma_cursor = await db.execute(f'PRAGMA table_info("{table_name}")')
            pragma_rows = await pragma_cursor.fetchall()
            count_cursor = await db.execute(f'SELECT COUNT(*) as count FROM "{table_name}"')
            count_row = await count_cursor.fetchone()
            tables.append(
                TableInfo(
                    name=table_name,
                    columns=[dict(r) for r in pragma_rows],
                    rowCount=count_row["count"] if count_row else 0,
                )
            )
        return {"database": name, "tables": [t.model_dump() for t in tables]}


@router.post("/{name}/query")
async def query_database(name: str, request: QueryRequest) -> dict:
    db_path = _get_db_path(name)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    async with aiosqlite.connect(db_path) as db:
        sql = request.sql.strip()
        is_select = bool(re.match(r"^(SELECT|WITH|PRAGMA|EXPLAIN)", sql, re.I))
        try:
            if is_select:
                cursor = await db.execute(sql, request.params or [])
                rows = await cursor.fetchall()
                columns = [d[0] for d in cursor.description] if cursor.description else []
                results = [dict(zip(columns, row)) for row in rows]
                return {"results": results, "rowCount": len(results)}
            else:
                await db.execute(sql, request.params or [])
                await db.commit()
                return {"changes": db.total_changes, "lastInsertRowid": db.last_insert_rowid}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("")
async def create_database(request: CreateDatabaseRequest) -> dict:
    _ensure_dir()
    db_path = _get_db_path(request.name)
    if db_path.exists():
        raise HTTPException(status_code=409, detail="Database already exists")
    async with aiosqlite.connect(db_path) as db:
        await db.close()
    return {"name": request.name, "message": "Database created"}


@router.delete("/{name}")
async def delete_database(name: str) -> dict:
    db_path = _get_db_path(name)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    db_path.unlink()
    return {"message": f'Database "{name}" deleted'}
