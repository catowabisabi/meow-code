/**
 * Memory System Service.
 * Stores memories as markdown files with YAML frontmatter in ~/.claude/memory/.
 * Provides CRUD and keyword search over saved memories.
 */
import { homedir } from 'os'
import fs from 'fs/promises'
import path from 'path'
import crypto from 'crypto'

// ─── Types ───────────────────────────────────────────────────

export interface Memory {
  id: string
  type: 'user' | 'feedback' | 'project' | 'reference'
  name: string
  description: string
  content: string
  createdAt: number
  updatedAt: number
}

type MemoryInput = Omit<Memory, 'id' | 'createdAt' | 'updatedAt'>

// ─── Paths ───────────────────────────────────────────────────

function getMemoryDir(): string {
  return path.join(homedir(), '.claude', 'memory')
}

function getIndexPath(): string {
  return path.join(getMemoryDir(), 'MEMORY.md')
}

async function ensureMemoryDir(): Promise<void> {
  await fs.mkdir(getMemoryDir(), { recursive: true })
}

/**
 * Convert a name into a filesystem-safe slug.
 */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
}

/**
 * Build the filename for a memory: {type}_{slug}.md
 */
function memoryFilename(type: string, name: string): string {
  return `${type}_${slugify(name)}.md`
}

/**
 * Derive a stable ID from type + name.
 */
function memoryId(type: string, name: string): string {
  return crypto.createHash('sha256').update(`${type}:${name}`).digest('hex').slice(0, 12)
}

// ─── YAML Frontmatter Helpers ────────────────────────────────

function serializeMemory(memory: Memory): string {
  const lines = [
    '---',
    `id: ${memory.id}`,
    `type: ${memory.type}`,
    `name: ${memory.name}`,
    `description: ${memory.description}`,
    `createdAt: ${memory.createdAt}`,
    `updatedAt: ${memory.updatedAt}`,
    '---',
    '',
    memory.content,
  ]
  return lines.join('\n')
}

function parseMemory(raw: string): Memory | null {
  const fmMatch = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  if (!fmMatch) return null

  const frontmatter = fmMatch[1]!
  const content = fmMatch[2]!.trim()

  const fields: Record<string, string> = {}
  for (const line of frontmatter.split('\n')) {
    const colonIdx = line.indexOf(':')
    if (colonIdx === -1) continue
    const key = line.slice(0, colonIdx).trim()
    const value = line.slice(colonIdx + 1).trim()
    fields[key] = value
  }

  if (!fields.id || !fields.type || !fields.name) return null

  return {
    id: fields.id,
    type: fields.type as Memory['type'],
    name: fields.name,
    description: fields.description || '',
    content,
    createdAt: parseInt(fields.createdAt || '0', 10),
    updatedAt: parseInt(fields.updatedAt || '0', 10),
  }
}

// ─── CRUD Operations ─────────────────────────────────────────

/**
 * Save a new memory. Returns the created Memory with generated id and timestamps.
 * Also updates the MEMORY.md index.
 */
export async function saveMemory(input: MemoryInput): Promise<Memory> {
  await ensureMemoryDir()

  const now = Date.now()
  const id = memoryId(input.type, input.name)

  const memory: Memory = {
    id,
    type: input.type,
    name: input.name,
    description: input.description,
    content: input.content,
    createdAt: now,
    updatedAt: now,
  }

  // Check if an existing memory has this id (update case)
  const existing = await getMemoryById(id)
  if (existing) {
    memory.createdAt = existing.createdAt
  }

  const filename = memoryFilename(input.type, input.name)
  const filePath = path.join(getMemoryDir(), filename)
  await fs.writeFile(filePath, serializeMemory(memory), 'utf-8')

  // Update index
  await rebuildIndex()

  return memory
}

/**
 * Get a memory by ID. Scans all files to find the matching one.
 */
async function getMemoryById(id: string): Promise<Memory | null> {
  const memories = await listMemories()
  return memories.find((m) => m.id === id) || null
}

/**
 * Get a memory by ID (public API).
 */
export async function getMemory(id: string): Promise<Memory | null> {
  return getMemoryById(id)
}

/**
 * List all memories.
 */
export async function listMemories(): Promise<Memory[]> {
  await ensureMemoryDir()

  const dir = getMemoryDir()
  let entries: string[]
  try {
    entries = await fs.readdir(dir)
  } catch {
    return []
  }

  const memories: Memory[] = []

  for (const entry of entries) {
    if (!entry.endsWith('.md') || entry === 'MEMORY.md') continue

    const filePath = path.join(dir, entry)
    try {
      const raw = await fs.readFile(filePath, 'utf-8')
      const memory = parseMemory(raw)
      if (memory) memories.push(memory)
    } catch {
      // Skip malformed files
    }
  }

  // Sort by updatedAt descending
  memories.sort((a, b) => b.updatedAt - a.updatedAt)
  return memories
}

/**
 * Delete a memory by ID.
 */
export async function deleteMemory(id: string): Promise<void> {
  await ensureMemoryDir()

  const dir = getMemoryDir()
  const entries = await fs.readdir(dir)

  for (const entry of entries) {
    if (!entry.endsWith('.md') || entry === 'MEMORY.md') continue

    const filePath = path.join(dir, entry)
    try {
      const raw = await fs.readFile(filePath, 'utf-8')
      const memory = parseMemory(raw)
      if (memory && memory.id === id) {
        await fs.unlink(filePath)
        break
      }
    } catch {
      // Skip
    }
  }

  // Rebuild index after deletion
  await rebuildIndex()
}

/**
 * Search memories by keyword matching on name, description, and content.
 */
export async function searchMemories(query: string): Promise<Memory[]> {
  const memories = await listMemories()
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean)

  if (terms.length === 0) return memories

  return memories.filter((m) => {
    const haystack = `${m.name} ${m.description} ${m.content}`.toLowerCase()
    return terms.every((term) => haystack.includes(term))
  })
}

// ─── MEMORY.md Index ─────────────────────────────────────────

/**
 * Rebuild the MEMORY.md index file from all memory files.
 */
async function rebuildIndex(): Promise<void> {
  const memories = await listMemories()
  const lines = ['# Memory Index', '']

  // Group by type
  const groups = new Map<string, Memory[]>()
  for (const m of memories) {
    const list = groups.get(m.type) || []
    list.push(m)
    groups.set(m.type, list)
  }

  for (const [type, mems] of groups) {
    lines.push(`## ${type}`)
    lines.push('')
    for (const m of mems) {
      lines.push(`- **${m.name}** (${m.id}): ${m.description}`)
    }
    lines.push('')
  }

  if (memories.length === 0) {
    lines.push('No memories stored yet.')
    lines.push('')
  }

  await fs.writeFile(getIndexPath(), lines.join('\n'), 'utf-8')
}

/**
 * Get the MEMORY.md index content.
 */
export async function getMemoryIndex(): Promise<string> {
  await ensureMemoryDir()

  try {
    return await fs.readFile(getIndexPath(), 'utf-8')
  } catch {
    // Generate if missing
    await rebuildIndex()
    try {
      return await fs.readFile(getIndexPath(), 'utf-8')
    } catch {
      return '# Memory Index\n\nNo memories stored yet.\n'
    }
  }
}
