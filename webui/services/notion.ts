/**
 * Notion API Client.
 * Full Notion control via REST API using fetch() directly.
 * No SDK dependency — works with Bun's built-in fetch.
 */
import { readModelsConfig } from '../config/modelsConfig.js'

// ─── Types ───────────────────────────────────────────────────

export interface NotionConfig {
  apiKey: string
  version?: string
}

// ─── Client ─────────────────────────────────────────────────

export class NotionClient {
  private apiKey: string
  private baseUrl = 'https://api.notion.com/v1'
  private version: string

  constructor(config: NotionConfig) {
    this.apiKey = config.apiKey
    this.version = config.version || '2022-06-28'
  }

  // ── Generic request helper ──

  private async request(method: string, path: string, body?: unknown): Promise<unknown> {
    const url = `${this.baseUrl}${path}`
    const headers: Record<string, string> = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Notion-Version': this.version,
      'Content-Type': 'application/json',
    }

    const opts: RequestInit = { method, headers }
    if (body && (method === 'POST' || method === 'PATCH' || method === 'PUT')) {
      opts.body = JSON.stringify(body)
    }

    const res = await fetch(url, opts)
    const data = await res.json()

    if (!res.ok) {
      const msg = (data as Record<string, unknown>).message || res.statusText
      throw new Error(`Notion API ${res.status}: ${msg}`)
    }

    return data
  }

  /** Auto-paginate a list endpoint */
  private async paginate(method: string, path: string, body?: Record<string, unknown>): Promise<unknown[]> {
    const results: unknown[] = []
    let cursor: string | undefined

    while (true) {
      const reqBody = { ...body, start_cursor: cursor, page_size: 100 }
      const data = await this.request(method, path, method === 'POST' ? reqBody : undefined) as Record<string, unknown>
      const items = data.results as unknown[]
      if (items) results.push(...items)

      if (!data.has_more || !data.next_cursor) break
      cursor = data.next_cursor as string
    }

    return results
  }

  // ── Pages ──

  async getPage(pageId: string) {
    return this.request('GET', `/pages/${pageId}`)
  }

  async createPage(parentId: string, properties: Record<string, unknown>, children?: unknown[]) {
    const body: Record<string, unknown> = {
      parent: { page_id: parentId },
      properties,
    }
    if (children) body.children = children
    return this.request('POST', '/pages', body)
  }

  async createPageInDatabase(databaseId: string, properties: Record<string, unknown>, children?: unknown[]) {
    const body: Record<string, unknown> = {
      parent: { database_id: databaseId },
      properties,
    }
    if (children) body.children = children
    return this.request('POST', '/pages', body)
  }

  async updatePage(pageId: string, properties: Record<string, unknown>) {
    return this.request('PATCH', `/pages/${pageId}`, { properties })
  }

  async archivePage(pageId: string) {
    return this.request('PATCH', `/pages/${pageId}`, { archived: true })
  }

  // ── Databases ──

  async getDatabase(dbId: string) {
    return this.request('GET', `/databases/${dbId}`)
  }

  async queryDatabase(dbId: string, filter?: unknown, sorts?: unknown[]) {
    const body: Record<string, unknown> = {}
    if (filter) body.filter = filter
    if (sorts) body.sorts = sorts
    return this.paginate('POST', `/databases/${dbId}/query`, body)
  }

  async createDatabase(parentId: string, title: string, properties: Record<string, unknown>) {
    return this.request('POST', '/databases', {
      parent: { page_id: parentId },
      title: [{ type: 'text', text: { content: title } }],
      properties,
    })
  }

  // ── Blocks (content) ──

  async getBlock(blockId: string) {
    return this.request('GET', `/blocks/${blockId}`)
  }

  async getBlockChildren(blockId: string): Promise<unknown[]> {
    return this.paginate('GET', `/blocks/${blockId}/children`)
  }

  async appendBlocks(parentId: string, children: unknown[]) {
    return this.request('PATCH', `/blocks/${parentId}/children`, { children })
  }

  async updateBlock(blockId: string, content: unknown) {
    return this.request('PATCH', `/blocks/${blockId}`, content)
  }

  async deleteBlock(blockId: string) {
    return this.request('DELETE', `/blocks/${blockId}`)
  }

  // ── Search ──

  async search(query: string, filter?: { property: string; value: string }) {
    const body: Record<string, unknown> = { query }
    if (filter) body.filter = filter
    return this.request('POST', '/search', body)
  }

  // ── Users ──

  async listUsers() {
    return this.paginate('GET', '/users')
  }

  async getUser(userId: string) {
    return this.request('GET', `/users/${userId}`)
  }

  // ── Comments ──

  async getComments(blockId: string) {
    return this.request('GET', `/comments?block_id=${blockId}`)
  }

  async addComment(discussionId: string, richText: unknown[]) {
    return this.request('POST', '/comments', {
      discussion_id: discussionId,
      rich_text: richText,
    })
  }

  async addPageComment(pageId: string, richText: unknown[]) {
    return this.request('POST', '/comments', {
      parent: { page_id: pageId },
      rich_text: richText,
    })
  }

  // ── Block builders (helpers) ──

  static paragraph(text: string) {
    return {
      object: 'block',
      type: 'paragraph',
      paragraph: {
        rich_text: [{ type: 'text', text: { content: text } }],
      },
    }
  }

  static heading1(text: string) {
    return {
      object: 'block',
      type: 'heading_1',
      heading_1: {
        rich_text: [{ type: 'text', text: { content: text } }],
      },
    }
  }

  static heading2(text: string) {
    return {
      object: 'block',
      type: 'heading_2',
      heading_2: {
        rich_text: [{ type: 'text', text: { content: text } }],
      },
    }
  }

  static todoItem(text: string, checked = false) {
    return {
      object: 'block',
      type: 'to_do',
      to_do: {
        rich_text: [{ type: 'text', text: { content: text } }],
        checked,
      },
    }
  }

  static bulletedListItem(text: string) {
    return {
      object: 'block',
      type: 'bulleted_list_item',
      bulleted_list_item: {
        rich_text: [{ type: 'text', text: { content: text } }],
      },
    }
  }

  static codeBlock(code: string, language = 'plain text') {
    return {
      object: 'block',
      type: 'code',
      code: {
        rich_text: [{ type: 'text', text: { content: code } }],
        language,
      },
    }
  }
}

// ─── Singleton ──────────────────────────────────────────────

let _client: NotionClient | null = null

export function getNotionClient(): NotionClient {
  if (_client) return _client

  const config = readModelsConfig()
  const notionConfig = (config as Record<string, unknown>).notion as NotionConfig | undefined

  if (!notionConfig?.apiKey) {
    throw new Error('Notion API key not configured. Add "notion": { "apiKey": "ntn_..." } to ~/.claude/models.json')
  }

  _client = new NotionClient(notionConfig)
  return _client
}

export function clearNotionClient(): void {
  _client = null
}
