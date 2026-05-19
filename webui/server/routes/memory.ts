/**
 * Memory API routes.
 */
import { saveMemory, getMemory, listMemories, deleteMemory, searchMemories, getMemoryIndex } from '../../services/memory.js'

export function registerMemoryRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/memory — List all memories
  router.set('GET:/api/memory', async () => {
    const memories = await listMemories()
    return Response.json({ memories, count: memories.length })
  })

  // GET /api/memory/index — Get MEMORY.md content
  router.set('GET:/api/memory/index', async () => {
    const index = await getMemoryIndex()
    return Response.json({ index })
  })

  // GET /api/memory/search — Search memories
  router.set('GET:/api/memory/search', async (req) => {
    const url = new URL(req.url)
    const q = url.searchParams.get('q') || ''
    const results = await searchMemories(q)
    return Response.json({ results, count: results.length })
  })

  // GET /api/memory/:id — Get a memory by ID
  router.set('GET:/api/memory/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!
    const memory = await getMemory(id)
    if (!memory) return Response.json({ error: 'Memory not found' }, { status: 404 })
    return Response.json(memory)
  })

  // POST /api/memory — Save a memory
  router.set('POST:/api/memory', async (req) => {
    const body = await req.json() as Record<string, unknown>
    const memory = await saveMemory({
      type: (body.type as string) || 'user',
      name: body.name as string,
      description: (body.description as string) || '',
      content: body.content as string,
    })
    return Response.json(memory)
  })

  // DELETE /api/memory/:id — Delete a memory
  router.set('DELETE:/api/memory/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!
    await deleteMemory(id)
    return Response.json({ ok: true })
  })
}
