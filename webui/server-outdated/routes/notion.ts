/**
 * Notion API routes — proxy to Notion REST API.
 */
import { getNotionClient } from '../../services/notion.js'

export function registerNotionRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/notion/search — Search Notion workspace
  router.set('GET:/api/notion/search', async (req) => {
    try {
      const url = new URL(req.url)
      const q = url.searchParams.get('q') || ''
      const type = url.searchParams.get('type') || undefined
      const client = getNotionClient()
      const filter = type ? { property: 'object', value: type } : undefined
      const result = await client.search(q, filter)
      return Response.json(result)
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // GET /api/notion/pages/:id — Read a page
  router.set('GET:/api/notion/pages/:id', async (req) => {
    try {
      const url = new URL(req.url)
      const id = url.pathname.split('/').pop()!
      const client = getNotionClient()
      const [page, blocks] = await Promise.all([
        client.getPage(id),
        client.getBlockChildren(id),
      ])
      return Response.json({ page, blocks })
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // POST /api/notion/pages — Create a page
  router.set('POST:/api/notion/pages', async (req) => {
    try {
      const body = await req.json() as Record<string, unknown>
      const client = getNotionClient()
      const result = await client.createPage(
        body.parentId as string,
        (body.properties || {}) as Record<string, unknown>,
        body.children as unknown[],
      )
      return Response.json(result)
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // GET /api/notion/databases/:id — Get database info
  router.set('GET:/api/notion/databases/:id', async (req) => {
    try {
      const url = new URL(req.url)
      const id = url.pathname.split('/').pop()!
      const client = getNotionClient()
      const result = await client.getDatabase(id)
      return Response.json(result)
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })

  // POST /api/notion/databases/:id/query — Query database
  router.set('POST:/api/notion/databases/:id/query', async (req) => {
    try {
      const url = new URL(req.url)
      const segments = url.pathname.split('/')
      const id = segments[segments.length - 2]!
      const body = await req.json() as Record<string, unknown>
      const client = getNotionClient()
      const results = await client.queryDatabase(id, body.filter, body.sorts as unknown[])
      return Response.json({ results })
    } catch (err: unknown) {
      return Response.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 })
    }
  })
}
