/**
 * Session Persistence Service.
 * Stores chat sessions as JSON files in ~/.claude/sessions/.
 */
import { homedir } from 'os'
import fs from 'fs/promises'
import path from 'path'
import type { UnifiedMessage, ContentBlock, TextBlock } from '../adapters/types.js'

// ─── Types ───────────────────────────────────────────────────

export interface StoredSession {
  id: string
  title: string
  mode: string
  folder: string | null
  model: string
  provider: string
  messages: UnifiedMessage[]
  createdAt: number
  updatedAt: number
  metadata?: Record<string, unknown>
}

interface SessionSummary {
  id: string
  title: string
  mode: string
  folder: string | null
  model: string
  updatedAt: number
}

// ─── Paths ───────────────────────────────────────────────────

function getSessionsDir(): string {
  return path.join(homedir(), '.claude', 'sessions')
}

function getSessionPath(sessionId: string): string {
  // Sanitize id to prevent path traversal
  const safe = sessionId.replace(/[^a-zA-Z0-9_-]/g, '')
  return path.join(getSessionsDir(), `${safe}.json`)
}

async function ensureSessionsDir(): Promise<void> {
  await fs.mkdir(getSessionsDir(), { recursive: true })
}

// ─── Title Generation ────────────────────────────────────────

/**
 * Generate a title from the first user message, truncated to 50 chars.
 */
export function generateTitle(messages: UnifiedMessage[]): string {
  // Find first user message
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser) return 'Untitled Session'

  // Find first assistant message (AI response)
  const firstAssistant = messages.find((m) => m.role === 'assistant')

  let userText = ''
  let assistantText = ''

  // Extract user text
  const userContent = firstUser.content
  if (typeof userContent === 'string') {
    userText = userContent
  } else if (Array.isArray(userContent)) {
    const textBlock = userContent.find((b): b is TextBlock => b.type === 'text')
    if (textBlock) userText = textBlock.text
  }

  // Extract assistant text (if exists)
  if (firstAssistant) {
    const assistantContent = firstAssistant.content
    if (typeof assistantContent === 'string') {
      assistantText = assistantContent
    } else if (Array.isArray(assistantContent)) {
      const textBlock = assistantContent.find((b): b is TextBlock => b.type === 'text')
      if (textBlock) assistantText = textBlock.text
    }
  }

  // Use the USER's first message as a temporary title
  // generateSmartTitle will later replace it with a concise AI-generated topic
  if (!userText) return '新的對話'
  const trimmed = userText.replace(/\s+/g, ' ').trim()
  if (trimmed.length === 0) return '新的對話'
  // Cap at 20 chars to keep titles concise
  if (trimmed.length <= 20) return trimmed
  // Find word boundary near 17 chars
  const nearBoundary = trimmed.slice(0, 20)
  const lastSpace = nearBoundary.lastIndexOf(' ')
  if (lastSpace > 10) return trimmed.slice(0, lastSpace) + '...'
  return trimmed.slice(0, 17) + '...'
}

// ─── CRUD Operations ─────────────────────────────────────────

/**
 * Save a session to disk.
 */
export async function saveSession(session: StoredSession): Promise<void> {
  await ensureSessionsDir()

  // Auto-generate title if empty
  if (!session.title) {
    session.title = generateTitle(session.messages)
  }

  session.updatedAt = Date.now()
  const filePath = getSessionPath(session.id)
  await fs.writeFile(filePath, JSON.stringify(session, null, 2), 'utf-8')
}

/**
 * Load a session by ID. Returns null if not found.
 */
export async function loadSession(sessionId: string): Promise<StoredSession | null> {
  const filePath = getSessionPath(sessionId)
  try {
    const raw = await fs.readFile(filePath, 'utf-8')
    return JSON.parse(raw) as StoredSession
  } catch {
    return null
  }
}

/**
 * List all saved sessions (metadata only, no full messages).
 * Sorted by updatedAt descending (most recent first).
 */
export async function listSessions(limit?: number): Promise<SessionSummary[]> {
  await ensureSessionsDir()

  const dir = getSessionsDir()
  let entries: string[]
  try {
    entries = await fs.readdir(dir)
  } catch {
    return []
  }

  const summaries: SessionSummary[] = []

  for (const entry of entries) {
    if (!entry.endsWith('.json')) continue

    const filePath = path.join(dir, entry)
    try {
      const raw = await fs.readFile(filePath, 'utf-8')
      const session = JSON.parse(raw) as StoredSession
      // Only include valid chat sessions (must have id, title, and messages array)
      if (!session.id || !session.messages || !Array.isArray(session.messages)) continue
      summaries.push({
        id: session.id,
        title: session.title,
        mode: session.mode || 'chat',
        folder: session.folder || null,
        model: session.model,
        updatedAt: session.updatedAt,
      })
    } catch {
      // Skip malformed files
    }
  }

  // Sort by most recently updated
  summaries.sort((a, b) => b.updatedAt - a.updatedAt)

  if (limit && limit > 0) {
    return summaries.slice(0, limit)
  }

  return summaries
}

/**
 * Delete a session by ID.
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const filePath = getSessionPath(sessionId)
  try {
    await fs.unlink(filePath)
  } catch {
    // Ignore if file doesn't exist
  }
}
