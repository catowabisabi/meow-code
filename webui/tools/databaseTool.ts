/**
 * SQLite Database Tool — AI can create, query, and manage SQLite databases.
 * Databases stored in ~/.claude/databases/
 */
import * as path from 'path'
import * as fs from 'fs'
import { Database } from 'bun:sqlite'
import type { ToolDef } from './types.js'

const DB_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '.', '.claude', 'databases')

function ensureDir() {
  if (!fs.existsSync(DB_DIR)) fs.mkdirSync(DB_DIR, { recursive: true })
}

function getDbPath(name: string): string {
  // Sanitize name
  const safe = name.replace(/[^a-zA-Z0-9_-]/g, '_')
  return path.join(DB_DIR, `${safe}.db`)
}

function openDb(name: string): Database {
  ensureDir()
  const dbPath = getDbPath(name)
  return new Database(dbPath)
}

export const databaseTool: ToolDef = {
  name: 'database',
  description: `SQLite database tool. Create, query, and manage local SQLite databases.

Actions:
- "create_table": Create a new table. Params: database (string), sql (CREATE TABLE statement)
- "query": Run a SELECT query. Params: database (string), sql (SELECT statement)
- "execute": Run INSERT/UPDATE/DELETE/ALTER. Params: database (string), sql (statement), params? (array of values for ? placeholders)
- "list_databases": List all databases
- "list_tables": List tables in a database. Params: database (string)
- "describe_table": Get table schema. Params: database (string), table (string)
- "export_csv": Export a table or query result as CSV. Params: database (string), sql? (SELECT query, default all rows), table? (table name if no sql)
- "drop_table": Drop a table. Params: database (string), table (string)
- "import_data": Insert multiple rows. Params: database (string), table (string), columns (string[]), rows (any[][])

Databases are stored in ~/.claude/databases/ as .db files.`,
  inputSchema: {
    type: 'object',
    properties: {
      action: {
        type: 'string',
        enum: ['create_table', 'query', 'execute', 'list_databases', 'list_tables', 'describe_table', 'export_csv', 'drop_table', 'import_data'],
        description: 'The action to perform',
      },
      database: { type: 'string', description: 'Database name (without .db extension)' },
      sql: { type: 'string', description: 'SQL statement to execute' },
      table: { type: 'string', description: 'Table name (for describe_table, export_csv, drop_table, import_data)' },
      params: { type: 'array', description: 'Parameters for parameterized queries (? placeholders)' },
      columns: { type: 'array', items: { type: 'string' }, description: 'Column names for import_data' },
      rows: { type: 'array', items: { type: 'array' }, description: 'Row data for import_data' },
    },
    required: ['action'],
  },
  isReadOnly: false,
  riskLevel: 'medium',
  execute: async (input: Record<string, unknown>) => {
    const action = input.action as string
    const dbName = input.database as string | undefined
    const sql = input.sql as string | undefined
    const table = input.table as string | undefined
    const params = input.params as unknown[] | undefined
    const columns = input.columns as string[] | undefined
    const rows = input.rows as unknown[][] | undefined

    try {
      switch (action) {
        case 'list_databases': {
          ensureDir()
          const files = fs.readdirSync(DB_DIR).filter(f => f.endsWith('.db'))
          const dbs = files.map(f => {
            const stat = fs.statSync(path.join(DB_DIR, f))
            return {
              name: f.replace('.db', ''),
              size: `${(stat.size / 1024).toFixed(1)} KB`,
              modified: new Date(stat.mtimeMs).toISOString(),
            }
          })
          return { output: JSON.stringify({ databases: dbs, count: dbs.length, directory: DB_DIR }, null, 2), isError: false }
        }

        case 'list_tables': {
          if (!dbName) return { output: 'Error: database name is required', isError: true }
          const db = openDb(dbName)
          try {
            const tables = db.query("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all()
            return { output: JSON.stringify({ database: dbName, tables }, null, 2), isError: false }
          } finally {
            db.close()
          }
        }

        case 'describe_table': {
          if (!dbName || !table) return { output: 'Error: database and table are required', isError: true }
          const db = openDb(dbName)
          try {
            const info = db.query(`PRAGMA table_info("${table}")`).all()
            const count = db.query(`SELECT COUNT(*) as count FROM "${table}"`).get() as Record<string, number>
            return { output: JSON.stringify({ database: dbName, table, columns: info, rowCount: count?.count || 0 }, null, 2), isError: false }
          } finally {
            db.close()
          }
        }

        case 'create_table': {
          if (!dbName || !sql) return { output: 'Error: database and sql are required', isError: true }
          const db = openDb(dbName)
          try {
            db.exec(sql)
            return { output: `Table created successfully in database "${dbName}".`, isError: false }
          } finally {
            db.close()
          }
        }

        case 'query': {
          if (!dbName || !sql) return { output: 'Error: database and sql are required', isError: true }
          if (!sql.trim().toUpperCase().startsWith('SELECT') && !sql.trim().toUpperCase().startsWith('WITH') && !sql.trim().toUpperCase().startsWith('PRAGMA')) {
            return { output: 'Error: query action only supports SELECT/WITH/PRAGMA statements. Use "execute" for modifications.', isError: true }
          }
          const db = openDb(dbName)
          try {
            const results = params ? db.query(sql).all(...params) : db.query(sql).all()
            const outputStr = JSON.stringify({ database: dbName, results, rowCount: results.length }, null, 2)
            return { output: outputStr.length > 50000 ? outputStr.slice(0, 50000) + '\n... (truncated)' : outputStr, isError: false }
          } finally {
            db.close()
          }
        }

        case 'execute': {
          if (!dbName || !sql) return { output: 'Error: database and sql are required', isError: true }
          const db = openDb(dbName)
          try {
            const result = params ? db.run(sql, ...params) : db.run(sql)
            return {
              output: JSON.stringify({
                database: dbName,
                changes: result.changes,
                lastInsertRowid: Number(result.lastInsertRowid),
                message: `Executed successfully. ${result.changes} row(s) affected.`,
              }, null, 2),
              isError: false,
            }
          } finally {
            db.close()
          }
        }

        case 'import_data': {
          if (!dbName || !table || !columns || !rows) return { output: 'Error: database, table, columns, and rows are required', isError: true }
          const db = openDb(dbName)
          try {
            const placeholders = columns.map(() => '?').join(', ')
            const stmt = db.prepare(`INSERT INTO "${table}" (${columns.map(c => `"${c}"`).join(', ')}) VALUES (${placeholders})`)
            let count = 0
            db.exec('BEGIN TRANSACTION')
            for (const row of rows) {
              stmt.run(...row)
              count++
            }
            db.exec('COMMIT')
            return { output: JSON.stringify({ database: dbName, table, rowsInserted: count, message: `Imported ${count} rows.` }, null, 2), isError: false }
          } catch (err) {
            db.exec('ROLLBACK')
            throw err
          } finally {
            db.close()
          }
        }

        case 'export_csv': {
          if (!dbName) return { output: 'Error: database is required', isError: true }
          const db = openDb(dbName)
          try {
            const query = sql || (table ? `SELECT * FROM "${table}"` : null)
            if (!query) return { output: 'Error: either sql or table is required', isError: true }
            const results = db.query(query).all() as Record<string, unknown>[]
            if (results.length === 0) return { output: 'No data to export.', isError: false }
            const headers = Object.keys(results[0]!)
            const csvLines = [headers.join(',')]
            for (const row of results) {
              csvLines.push(headers.map(h => {
                const val = row[h]
                const str = val === null ? '' : String(val)
                return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str.replace(/"/g, '""')}"` : str
              }).join(','))
            }
            const csv = csvLines.join('\n')
            return { output: csv.length > 50000 ? csv.slice(0, 50000) + '\n... (truncated)' : csv, isError: false }
          } finally {
            db.close()
          }
        }

        case 'drop_table': {
          if (!dbName || !table) return { output: 'Error: database and table are required', isError: true }
          const db = openDb(dbName)
          try {
            db.exec(`DROP TABLE IF EXISTS "${table}"`)
            return { output: `Table "${table}" dropped from database "${dbName}".`, isError: false }
          } finally {
            db.close()
          }
        }

        default:
          return { output: `Unknown action: ${action}`, isError: true }
      }
    } catch (err: unknown) {
      return { output: `Database error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
