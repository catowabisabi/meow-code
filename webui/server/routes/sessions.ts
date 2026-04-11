/**
 * REST API routes for session/history management.
 * Combines in-memory active sessions with persistent storage.
 */
import { getAllSessions, getSession, createSession } from '../ws/chatSocket.js'
import {
  saveSession,
  loadSession,
  listSessions as listStoredSessions,
  deleteSession,
  generateTitle,
} from '../../services/sessionStore.js'

export function registerSessionRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // POST /api/sessions — Create a new chat session
  router.set('POST:/api/sessions', async () => {
    const session = createSession()
    return Response.json({
      id: session.id,
      model: session.model,
      provider: session.provider,
      messageCount: 0,
      createdAt: session.createdAt,
      preview: '(new session)',
    })
  })

  // GET /api/sessions — List all chat sessions (merge in-memory + stored)
  router.set('GET:/api/sessions', async () => {
    // Get in-memory active sessions
    const activeSessions = getAllSessions()
    const activeSummaries = activeSessions.map((s) => ({
      id: s.id,
      title: s.title || generateTitle(s.messages),
      model: s.model,
      provider: s.provider,
      messageCount: s.messages.length,
      created_at: new Date(s.createdAt).toISOString(),
      mode: (s as any).mode || 'chat',
      folder: (s as any).folder || null,
      preview: getPreview(s.messages),
    }))

    // Get stored sessions from disk
    const storedSessions = await listStoredSessions()
    const activeIds = new Set(activeSummaries.map((s) => s.id))
    const storedSummaries = storedSessions
      .filter((s) => s.id && !activeIds.has(s.id)) // skip bad entries + duplicates
      .map((s) => ({
        id: s.id,
        title: s.title || `Chat ${(s.id || '').slice(0, 8)}...`,
        model: s.model || '',
        provider: '',
        messageCount: 0,
        created_at: new Date(s.updatedAt || Date.now()).toISOString(),
        mode: s.mode || 'chat',
        folder: s.folder || null,
        preview: '',
      }))

    // Merge and sort by date descending
    const all = [...activeSummaries, ...storedSummaries]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    return Response.json({ sessions: all })
  })

  // GET /api/sessions/:id — Get full session (checks in-memory first, then disk)
  router.set('GET:/api/sessions/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!

    // Check in-memory first
    const session = getSession(id)
    if (session) {
      return Response.json({
        id: session.id,
        model: session.model,
        provider: session.provider,
        messages: session.messages,
        createdAt: session.createdAt,
      })
    }

    // Check persistent storage
    const stored = await loadSession(id)
    if (stored) {
      return Response.json(stored)
    }

    return Response.json({ error: 'Session not found' }, { status: 404 })
  })

  // GET /api/sessions/stored/list — List all persistently saved sessions
  router.set('GET:/api/sessions/stored/list', async (req) => {
    const url = new URL(req.url)
    const limitParam = url.searchParams.get('limit')
    const limit = limitParam ? parseInt(limitParam, 10) : undefined
    const sessions = await listStoredSessions(limit)
    return Response.json({ sessions })
  })

  // POST /api/sessions/:id/save — Save an active session to persistent storage
  router.set('POST:/api/sessions/:id/save', async (req) => {
    const url = new URL(req.url)
    const segments = url.pathname.split('/')
    const id = segments[segments.length - 2]!

    // Get active session
    const session = getSession(id)
    if (!session) {
      return Response.json({ error: 'Active session not found' }, { status: 404 })
    }

    // Optional metadata from request body
    let metadata: Record<string, unknown> | undefined
    try {
      const body = await req.json() as { metadata?: Record<string, unknown> }
      metadata = body.metadata
    } catch {
      // No body is fine
    }

    await saveSession({
      id: session.id,
      title: generateTitle(session.messages),
      mode: (session as any).mode || 'chat',
      folder: (session as any).folder || null,
      model: session.model,
      provider: session.provider,
      messages: session.messages,
      createdAt: session.createdAt,
      updatedAt: Date.now(),
      metadata,
    })

    return Response.json({ ok: true, id: session.id })
  })

  // DELETE /api/sessions/:id — Delete a persisted session
  router.set('DELETE:/api/sessions/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!
    await deleteSession(id)
    return Response.json({ ok: true })
  })

  // PUT /api/sessions/:id — Update session title
  router.set('PUT:/api/sessions/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!

    let body: { title?: string } = {}
    try {
      body = await req.json()
    } catch {
      return Response.json({ error: 'Invalid JSON' }, { status: 400 })
    }

    if (typeof body.title !== 'string') {
      return Response.json({ error: 'Missing or invalid title' }, { status: 400 })
    }

    const session = getSession(id)
    if (session) {
      session.title = body.title
      return Response.json({ ok: true, id, title: body.title })
    }

    const stored = await loadSession(id)
    if (stored) {
      stored.title = body.title
      await saveSession(stored)
      return Response.json({ ok: true, id, title: body.title })
    }

    return Response.json({ error: 'Session not found' }, { status: 404 })
  })
}

function getPreview(messages: Array<{ role: string; content: unknown }>): string {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser) return '(empty)'

  const content = firstUser.content
  if (typeof content === 'string') return content.slice(0, 100)
  if (Array.isArray(content)) {
    const textBlock = content.find((b: Record<string, unknown>) => b.type === 'text') as
      | { text: string }
      | undefined
    if (textBlock) return textBlock.text.slice(0, 100)
  }
  return '(media)'
}
