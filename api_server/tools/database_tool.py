"""SQLite Database Tool — create, query, and manage local SQLite databases."""
import json
import os
import re
from typing import Any, Dict, List, Optional

import aiosqlite

from .types import ToolDef, ToolResult, ToolContext

DB_DIR = os.path.join(os.path.expanduser("~"), ".claude", "databases")
MAX_OUTPUT_SIZE = 50000
MAX_ROW_LIMIT = 1000


def _ensure_dir() -> None:
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)


def _get_db_path(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return os.path.join(DB_DIR, f"{safe}.db")


async def _open_db(name: str) -> aiosqlite.Connection:
    _ensure_dir()
    db_path = _get_db_path(name)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db


async def _list_databases_impl() -> str:
    _ensure_dir()
    files = [f for f in os.listdir(DB_DIR) if f.endswith(".db")]
    dbs = []
    for f in files:
        stat = os.stat(os.path.join(DB_DIR, f))
        dbs.append({
            "name": f[:-3],
            "size": f"{(stat.st_size / 1024):.1f} KB",
            "modified": stat.st_mtime,
        })
    return json.dumps({"databases": dbs, "count": len(dbs), "directory": DB_DIR}, indent=2)


async def _list_tables_impl(db: aiosqlite.Connection, db_name: str) -> str:
    cursor = await db.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    rows = await cursor.fetchall()
    tables = [{"name": row["name"], "sql": row["sql"]} for row in rows]
    return json.dumps({"database": db_name, "tables": tables}, indent=2)


async def _describe_table_impl(db: aiosqlite.Connection, db_name: str, table: str) -> str:
    cursor = await db.execute(f"PRAGMA table_info(\"{table}\")")
    columns = await cursor.fetchall()
    
    count_cursor = await db.execute(f'SELECT COUNT(*) as count FROM "{table}"')
    count_row = await count_cursor.fetchone()
    count = count_row["count"] if count_row else 0
    
    return json.dumps({
        "database": db_name,
        "table": table,
        "columns": [dict(row) for row in columns],
        "rowCount": count,
    }, indent=2)


async def _create_table_impl(db: aiosqlite.Connection, sql: str) -> str:
    await db.execute(sql)
    await db.commit()
    return "Table created successfully."


async def _query_impl(db: aiosqlite.Connection, db_name: str, sql: str, params: Optional[List] = None) -> str:
    if params:
        cursor = await db.execute(sql, params)
    else:
        cursor = await db.execute(sql)
    
    rows = await cursor.fetchall()
    
    if len(rows) > MAX_ROW_LIMIT:
        rows = rows[:MAX_ROW_LIMIT]
        truncated = True
    else:
        truncated = False
    
    results = [dict(row) for row in rows]
    output = json.dumps({
        "database": db_name,
        "results": results,
        "rowCount": len(results),
        "truncated": truncated,
    }, indent=2, default=str)
    
    if len(output) > MAX_OUTPUT_SIZE:
        output = output[:MAX_OUTPUT_SIZE] + "\n... (truncated)"
    
    return output


async def _execute_impl(db: aiosqlite.Connection, db_name: str, sql: str, params: Optional[List] = None) -> str:
    if params:
        cursor = await db.execute(sql, params)
    else:
        cursor = await db.execute(sql)
    
    await db.commit()
    changes = db.total_changes
    last_id = cursor.lastrowid if cursor.lastrowid else 0
    
    return json.dumps({
        "database": db_name,
        "changes": changes,
        "lastInsertRowid": last_id,
        "message": f"Executed successfully. {changes} row(s) affected.",
    }, indent=2)


async def _import_data_impl(db: aiosqlite.Connection, db_name: str, table: str, columns: List[str], rows: List[List]) -> str:
    placeholders = ", ".join(["?" for _ in columns])
    column_names = ", ".join([f'"{c}"' for c in columns])
    sql = f'INSERT INTO "{table}" ({column_names}) VALUES ({placeholders})'
    
    await db.execute("BEGIN TRANSACTION")
    try:
        count = 0
        for row in rows:
            await db.execute(sql, row)
            count += 1
        await db.commit()
        return json.dumps({
            "database": db_name,
            "table": table,
            "rowsInserted": count,
            "message": f"Imported {count} rows.",
        }, indent=2)
    except Exception:
        await db.execute("ROLLBACK")
        raise


async def _export_csv_impl(db: aiosqlite.Connection, sql: Optional[str], table: Optional[str]) -> str:
    if sql:
        query = sql
    elif table:
        query = f'SELECT * FROM "{table}"'
    else:
        return json.dumps({"error": "Either sql or table is required"}, indent=2)
    
    cursor = await db.execute(query)
    rows = await cursor.fetchall()
    
    if len(rows) == 0:
        return "No data to export."
    
    headers = list(rows[0].keys())
    csv_lines = [",".join(headers)]
    
    for row in rows:
        values = []
        for h in headers:
            val = row[h]
            if val is None:
                val_str = ""
            else:
                val_str = str(val)
                if "," in val_str or '"' in val_str or "\n" in val_str:
                    val_str = '"' + val_str.replace('"', '""') + '"'
            values.append(val_str)
        csv_lines.append(",".join(values))
    
    csv = "\n".join(csv_lines)
    
    if len(csv) > MAX_OUTPUT_SIZE:
        csv = csv[:MAX_OUTPUT_SIZE] + "\n... (truncated)"
    
    return csv


async def _drop_table_impl(db: aiosqlite.Connection, table: str) -> str:
    await db.execute(f'DROP TABLE IF EXISTS "{table}"')
    await db.commit()
    return f'Table "{table}" dropped successfully.'


DATABASE_TOOL = ToolDef(
    name="database",
    description="""SQLite database tool. Create, query, and manage local SQLite databases.

Actions:
- "create_table": Create a new table. Params: database (string), sql (CREATE TABLE statement)
- "query": Run a SELECT query. Params: database (string), sql (SELECT statement), params? (array of values for ? placeholders)
- "execute": Run INSERT/UPDATE/DELETE/ALTER. Params: database (string), sql (statement), params? (array of values for ? placeholders)
- "list_databases": List all databases
- "list_tables": List tables in a database. Params: database (string)
- "describe_table": Get table schema. Params: database (string), table (string)
- "export_csv": Export a table or query result as CSV. Params: database (string), sql? (SELECT query), table? (table name if no sql)
- "drop_table": Drop a table. Params: database (string), table (string)
- "import_data": Insert multiple rows. Params: database (string), table (string), columns (string[]), rows (any[][])

Databases are stored in ~/.claude/databases/ as .db files.""",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_table", "query", "execute", "list_databases", "list_tables", "describe_table", "export_csv", "drop_table", "import_data"],
                "description": "The action to perform",
            },
            "database": {"type": "string", "description": "Database name (without .db extension)"},
            "sql": {"type": "string", "description": "SQL statement to execute"},
            "table": {"type": "string", "description": "Table name (for describe_table, export_csv, drop_table, import_data)"},
            "params": {"type": "array", "description": "Parameters for parameterized queries (? placeholders)"},
            "columns": {"type": "array", "items": {"type": "string"}, "description": "Column names for import_data"},
            "rows": {"type": "array", "items": {"type": "array"}, "description": "Row data for import_data"},
        },
        "required": ["action"],
    },
    is_read_only=False,
    risk_level="medium",
    execute=lambda args, ctx: _database_execute(args, ctx),
)


async def _database_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, "tool_call_id", "") or ""
    
    action = args.get("action")
    db_name = args.get("database")
    sql = args.get("sql")
    table = args.get("table")
    params = args.get("params")
    columns = args.get("columns")
    rows = args.get("rows")
    
    try:
        if action == "list_databases":
            output = await _list_databases_impl()
            return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
        
        if action == "list_tables":
            if not db_name:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database name is required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _list_tables_impl(db, db_name)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "describe_table":
            if not db_name or not table:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database and table are required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _describe_table_impl(db, db_name, table)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "create_table":
            if not db_name or not sql:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database and sql are required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _create_table_impl(db, sql)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "query":
            if not db_name or not sql:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database and sql are required", is_error=True)
            sql_upper = sql.strip().upper()
            if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH") or sql_upper.startswith("PRAGMA")):
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output="Error: query action only supports SELECT/WITH/PRAGMA statements. Use 'execute' for modifications.",
                    is_error=True,
                )
            db = await _open_db(db_name)
            try:
                output = await _query_impl(db, db_name, sql, params)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "execute":
            if not db_name or not sql:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database and sql are required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _execute_impl(db, db_name, sql, params)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "import_data":
            if not db_name or not table or not columns or not rows:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database, table, columns, and rows are required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _import_data_impl(db, db_name, table, columns, rows)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "export_csv":
            if not db_name:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database is required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _export_csv_impl(db, sql, table)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        if action == "drop_table":
            if not db_name or not table:
                return ToolResult(tool_call_id=tool_call_id, output="Error: database and table are required", is_error=True)
            db = await _open_db(db_name)
            try:
                output = await _drop_table_impl(db, table)
                return ToolResult(tool_call_id=tool_call_id, output=output, is_error=False)
            finally:
                await db.close()
        
        return ToolResult(tool_call_id=tool_call_id, output=f"Unknown action: {action}", is_error=True)
    
    except Exception as err:
        return ToolResult(tool_call_id=tool_call_id, output=f"Database error: {err}", is_error=True)


__all__ = ["DATABASE_TOOL"]
