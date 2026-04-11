/**
 * Notion tools — full Notion workspace control for the AI agent.
 *
 * Tools:
 *   notion_search    — Search pages/databases
 *   notion_read_page — Read page properties + content blocks
 *   notion_write_page — Create or update pages
 *   notion_database  — Query/create/get databases
 *   notion_block     — Get/list/append/update/delete blocks
 */
import type { ToolDef, ToolResult } from './types.js'
import { getNotionClient, NotionClient } from '../services/notion.js'

// ─── Notion Search ──────────────────────────────────────────

export const notionSearchTool: ToolDef = {
  name: 'notion_search',
  description: 'Search your Notion workspace for pages and databases by keyword.',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'Search query' },
      type: { type: 'string', enum: ['page', 'database'], description: 'Filter by object type (optional)' },
    },
    required: ['query'],
  },
  isReadOnly: true,
  riskLevel: 'low',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    try {
      const client = getNotionClient()
      const filter = input.type ? { property: 'object', value: input.type as string } : undefined
      const result = await client.search(input.query as string, filter)
      return { output: JSON.stringify(result, null, 2).slice(0, 30000), isError: false }
    } catch (err: unknown) {
      return { output: `Notion search error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Notion Read Page ───────────────────────────────────────

export const notionReadPageTool: ToolDef = {
  name: 'notion_read_page',
  description: 'Read a Notion page: its properties and content blocks. Returns the page metadata and all child blocks.',
  inputSchema: {
    type: 'object',
    properties: {
      pageId: { type: 'string', description: 'The Notion page ID (UUID format, with or without dashes)' },
    },
    required: ['pageId'],
  },
  isReadOnly: true,
  riskLevel: 'low',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    try {
      const client = getNotionClient()
      const pageId = input.pageId as string
      const [page, blocks] = await Promise.all([
        client.getPage(pageId),
        client.getBlockChildren(pageId),
      ])
      const result = { page, blocks }
      return { output: JSON.stringify(result, null, 2).slice(0, 30000), isError: false }
    } catch (err: unknown) {
      return { output: `Notion read error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Notion Write Page ──────────────────────────────────────

export const notionWritePageTool: ToolDef = {
  name: 'notion_write_page',
  description: [
    'Create or update a Notion page.',
    'For "create": provide parentId (page or database), title, and optional content blocks.',
    'For "update": provide pageId and properties to update.',
    'Content items can be: { type: "paragraph"|"heading_1"|"heading_2"|"to_do"|"bulleted_list_item"|"code", text: "...", checked?: bool, language?: string }',
  ].join('\n'),
  inputSchema: {
    type: 'object',
    properties: {
      action: { type: 'string', enum: ['create', 'update', 'archive'], description: 'Action to perform' },
      parentId: { type: 'string', description: 'Parent page/database ID (for create)' },
      parentType: { type: 'string', enum: ['page', 'database'], description: 'Parent type (default: page)' },
      pageId: { type: 'string', description: 'Page ID (for update/archive)' },
      title: { type: 'string', description: 'Page title (for create)' },
      properties: { type: 'object', description: 'Page properties (Notion format)' },
      content: {
        type: 'array',
        description: 'Content blocks to add',
        items: {
          type: 'object',
          properties: {
            type: { type: 'string' },
            text: { type: 'string' },
            checked: { type: 'boolean' },
            language: { type: 'string' },
          },
        },
      },
    },
    required: ['action'],
  },
  isReadOnly: false,
  riskLevel: 'medium',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    try {
      const client = getNotionClient()
      const action = input.action as string

      if (action === 'archive') {
        const result = await client.archivePage(input.pageId as string)
        return { output: JSON.stringify(result, null, 2), isError: false }
      }

      if (action === 'update') {
        const props = (input.properties || {}) as Record<string, unknown>
        const result = await client.updatePage(input.pageId as string, props)
        return { output: JSON.stringify(result, null, 2).slice(0, 10000), isError: false }
      }

      if (action === 'create') {
        const parentId = input.parentId as string
        const parentType = (input.parentType as string) || 'page'
        const title = input.title as string || 'Untitled'

        // Build properties
        const props = (input.properties || {
          title: { title: [{ text: { content: title } }] },
        }) as Record<string, unknown>

        // Convert simple content array to Notion blocks
        const contentItems = (input.content || []) as Array<Record<string, unknown>>
        const children = contentItems.map((item) => {
          const text = (item.text as string) || ''
          switch (item.type) {
            case 'heading_1': return NotionClient.heading1(text)
            case 'heading_2': return NotionClient.heading2(text)
            case 'to_do': return NotionClient.todoItem(text, (item.checked as boolean) || false)
            case 'bulleted_list_item': return NotionClient.bulletedListItem(text)
            case 'code': return NotionClient.codeBlock(text, (item.language as string) || 'plain text')
            default: return NotionClient.paragraph(text)
          }
        })

        let result
        if (parentType === 'database') {
          result = await client.createPageInDatabase(parentId, props, children.length > 0 ? children : undefined)
        } else {
          result = await client.createPage(parentId, props, children.length > 0 ? children : undefined)
        }
        return { output: JSON.stringify(result, null, 2).slice(0, 10000), isError: false }
      }

      return { output: `Unknown action: ${action}`, isError: true }
    } catch (err: unknown) {
      return { output: `Notion write error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Notion Database Tool ───────────────────────────────────

export const notionDatabaseTool: ToolDef = {
  name: 'notion_database',
  description: [
    'Query, get, or create Notion databases.',
    '"query": Query a database with optional filter and sorts.',
    '"get": Get database schema/properties.',
    '"create": Create a new database under a parent page.',
  ].join('\n'),
  inputSchema: {
    type: 'object',
    properties: {
      action: { type: 'string', enum: ['query', 'get', 'create'], description: 'Action' },
      databaseId: { type: 'string', description: 'Database ID (for query/get)' },
      filter: { type: 'object', description: 'Notion filter object (for query)' },
      sorts: { type: 'array', description: 'Notion sorts array (for query)' },
      parentId: { type: 'string', description: 'Parent page ID (for create)' },
      title: { type: 'string', description: 'Database title (for create)' },
      properties: { type: 'object', description: 'Database properties schema (for create)' },
    },
    required: ['action'],
  },
  isReadOnly: false, // create is not read-only
  riskLevel: 'medium',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    try {
      const client = getNotionClient()
      const action = input.action as string

      if (action === 'get') {
        const result = await client.getDatabase(input.databaseId as string)
        return { output: JSON.stringify(result, null, 2).slice(0, 20000), isError: false }
      }

      if (action === 'query') {
        const results = await client.queryDatabase(
          input.databaseId as string,
          input.filter,
          input.sorts as unknown[],
        )
        return { output: JSON.stringify(results, null, 2).slice(0, 30000), isError: false }
      }

      if (action === 'create') {
        const result = await client.createDatabase(
          input.parentId as string,
          input.title as string || 'Untitled Database',
          (input.properties || {}) as Record<string, unknown>,
        )
        return { output: JSON.stringify(result, null, 2).slice(0, 10000), isError: false }
      }

      return { output: `Unknown action: ${action}`, isError: true }
    } catch (err: unknown) {
      return { output: `Notion database error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Notion Block Tool ──────────────────────────────────────

export const notionBlockTool: ToolDef = {
  name: 'notion_block',
  description: [
    'Manage Notion blocks (content elements within pages).',
    '"get": Get a single block.',
    '"list": List child blocks of a page/block.',
    '"append": Append new blocks to a page/block.',
    '"update": Update an existing block.',
    '"delete": Delete a block.',
  ].join('\n'),
  inputSchema: {
    type: 'object',
    properties: {
      action: { type: 'string', enum: ['get', 'list', 'append', 'update', 'delete'], description: 'Action' },
      blockId: { type: 'string', description: 'Block ID (for get/list/update/delete)' },
      parentId: { type: 'string', description: 'Parent page/block ID (for append)' },
      children: {
        type: 'array',
        description: 'Blocks to append (simplified: {type, text, checked?, language?})',
        items: { type: 'object' },
      },
      content: { type: 'object', description: 'Block content for update (raw Notion format)' },
    },
    required: ['action'],
  },
  isReadOnly: false,
  riskLevel: 'medium',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    try {
      const client = getNotionClient()
      const action = input.action as string

      if (action === 'get') {
        const result = await client.getBlock(input.blockId as string)
        return { output: JSON.stringify(result, null, 2), isError: false }
      }

      if (action === 'list') {
        const results = await client.getBlockChildren(input.blockId as string)
        return { output: JSON.stringify(results, null, 2).slice(0, 30000), isError: false }
      }

      if (action === 'append') {
        const items = (input.children || []) as Array<Record<string, unknown>>
        const blocks = items.map((item) => {
          const text = (item.text as string) || ''
          switch (item.type) {
            case 'heading_1': return NotionClient.heading1(text)
            case 'heading_2': return NotionClient.heading2(text)
            case 'to_do': return NotionClient.todoItem(text, (item.checked as boolean) || false)
            case 'bulleted_list_item': return NotionClient.bulletedListItem(text)
            case 'code': return NotionClient.codeBlock(text, (item.language as string) || 'plain text')
            default: return NotionClient.paragraph(text)
          }
        })
        const result = await client.appendBlocks(input.parentId as string, blocks)
        return { output: JSON.stringify(result, null, 2).slice(0, 10000), isError: false }
      }

      if (action === 'update') {
        const result = await client.updateBlock(input.blockId as string, input.content)
        return { output: JSON.stringify(result, null, 2), isError: false }
      }

      if (action === 'delete') {
        const result = await client.deleteBlock(input.blockId as string)
        return { output: JSON.stringify(result, null, 2), isError: false }
      }

      return { output: `Unknown action: ${action}`, isError: true }
    } catch (err: unknown) {
      return { output: `Notion block error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
