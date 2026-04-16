/**
 * Database API routes — SQLite database management from WebUI.
 */
import * as path from 'path'
import * as fs from 'fs'
import { Database } from 'bun:sqlite'

const DB_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '.', '.claude', 'databases')

function ensureDir() {
  if (!fs.existsSync(DB_DIR)) fs.mkdirSync(DB_DIR, { recursive: true })
}

function getDbPath(name: string): string {
  const safe = name.replace(/[^a-zA-Z0-9_-]/g, '_')
  return path.join(DB_DIR, `${safe}.db`)
}

export function registerDatabaseRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/databases — List all databases
  router.set('GET:/api/databases', async () => {
    try {
      ensureDir()
      const files = fs.readdirSync(DB_DIR).filter(f => f.endsWith('.db'))
      const databases = files.map(f => {
        const stat = fs.statSync(path.join(DB_DIR, f))
        return {
          name: f.replace('.db', ''),
          size: stat.size,
          sizeFormatted: `${(stat.size / 1024).toFixed(1)} KB`,
          modified: new Date(stat.mtimeMs).toISOString(),
        }
      })
      return Response.json({ databases })
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // GET /api/databases/:name/tables — List tables
  router.set('GET:/api/databases/:name/tables', async (req) => {
    try {
      const url = new URL(req.url)
      const name = url.pathname.split('/')[3]!
      const dbPath = getDbPath(name)
      if (!fs.existsSync(dbPath)) return Response.json({ error: 'Database not found' }, { status: 404 })
      const db = new Database(dbPath)
      try {
        const tables = db.query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all() as { name: string }[]
        const result = tables.map(t => {
          const info = db.query(`PRAGMA table_info("${t.name}")`).all()
          const count = db.query(`SELECT COUNT(*) as count FROM "${t.name}"`).get() as { count: number }
          return { name: t.name, columns: info, rowCount: count?.count || 0 }
        })
        return Response.json({ database: name, tables: result })
      } finally {
        db.close()
      }
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // POST /api/databases/:name/query — Execute SQL query
  router.set('POST:/api/databases/:name/query', async (req) => {
    try {
      const url = new URL(req.url)
      const name = url.pathname.split('/')[3]!
      const body = await req.json() as { sql: string; params?: unknown[] }
      const dbPath = getDbPath(name)
      if (!fs.existsSync(dbPath)) return Response.json({ error: 'Database not found' }, { status: 404 })
      const db = new Database(dbPath)
      try {
        const sql = body.sql.trim()
        const isSelect = /^(SELECT|WITH|PRAGMA|EXPLAIN)/i.test(sql)
        if (isSelect) {
          const results = body.params ? db.query(sql).all(...body.params) : db.query(sql).all()
          return Response.json({ results, rowCount: results.length })
        } else {
          const result = body.params ? db.run(sql, ...body.params) : db.run(sql)
          return Response.json({ changes: result.changes, lastInsertRowid: Number(result.lastInsertRowid) })
        }
      } finally {
        db.close()
      }
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // POST /api/databases — Create a new database
  router.set('POST:/api/databases', async (req) => {
    try {
      const body = await req.json() as { name: string }
      ensureDir()
      const dbPath = getDbPath(body.name)
      if (fs.existsSync(dbPath)) return Response.json({ error: 'Database already exists' }, { status: 409 })
      const db = new Database(dbPath)
      db.close()
      return Response.json({ name: body.name, message: 'Database created' })
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // DELETE /api/databases/:name — Delete a database
  router.set('DELETE:/api/databases/:name', async (req) => {
    try {
      const url = new URL(req.url)
      const name = url.pathname.split('/')[3]!
      const dbPath = getDbPath(name)
      if (!fs.existsSync(dbPath)) return Response.json({ error: 'Database not found' }, { status: 404 })
      fs.unlinkSync(dbPath)
      return Response.json({ message: `Database "${name}" deleted` })
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // POST /api/databases/:name/export — Export as CSV or JSON
  router.set('POST:/api/databases/:name/export', async (req) => {
    try {
      const url = new URL(req.url)
      const name = url.pathname.split('/')[3]!
      const body = await req.json() as { table?: string; sql?: string; format?: 'csv' | 'json' }
      const dbPath = getDbPath(name)
      if (!fs.existsSync(dbPath)) return Response.json({ error: 'Database not found' }, { status: 404 })
      const db = new Database(dbPath)
      try {
        const query = body.sql || (body.table ? `SELECT * FROM "${body.table}"` : null)
        if (!query) return Response.json({ error: 'table or sql required' }, { status: 400 })
        const results = db.query(query).all() as Record<string, unknown>[]
        if (body.format === 'csv' && results.length > 0) {
          const headers = Object.keys(results[0]!)
          const lines = [headers.join(',')]
          for (const row of results) {
            lines.push(headers.map(h => {
              const v = row[h]
              const s = v === null ? '' : String(v)
              return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
            }).join(','))
          }
          return new Response(lines.join('\n'), {
            headers: { 'Content-Type': 'text/csv', 'Content-Disposition': `attachment; filename="${name}_export.csv"` },
          })
        }
        return Response.json({ results, rowCount: results.length })
      } finally {
        db.close()
      }
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })
}
