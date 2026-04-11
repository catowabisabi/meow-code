/**
 * Memory tools — allow the AI to save and retrieve persistent memories.
 */
import type { ToolDef, ToolResult } from './types.js'
import {
  saveMemory,
  getMemory,
  listMemories,
  deleteMemory,
  searchMemories,
  getMemoryIndex,
} from '../services/memory.js'

// ─── Memory Write Tool ───────────────────────────────────────

export const memoryWriteTool: ToolDef = {
  name: 'memory_write',
  description:
    'Save, delete, list, or search persistent memories. ' +
    'Use this to remember user preferences, project context, important decisions, and reference material.',
  inputSchema: {
    type: 'object',
    required: ['action'],
    properties: {
      action: {
        type: 'string',
        enum: ['save', 'list', 'search', 'delete'],
        description: 'Action to perform',
      },
      type: {
        type: 'string',
        enum: ['user', 'feedback', 'project', 'reference'],
        description: 'Memory type (required for save)',
      },
      name: {
        type: 'string',
        description: 'Short name/title for the memory (required for save)',
      },
      description: {
        type: 'string',
        description: 'Brief description of what this memory contains (required for save)',
      },
      content: {
        type: 'string',
        description: 'Full content of the memory (required for save)',
      },
      query: {
        type: 'string',
        description: 'Search query (required for search)',
      },
      id: {
        type: 'string',
        description: 'Memory ID (required for delete)',
      },
    },
  },
  isReadOnly: false,
  riskLevel: 'low',
  async execute(input): Promise<ToolResult> {
    try {
      const action = input.action as string

      switch (action) {
        case 'save': {
          const type = input.type as 'user' | 'feedback' | 'project' | 'reference'
          const name = input.name as string
          const description = input.description as string
          const content = input.content as string

          if (!type || !name || !description || !content) {
            return {
              output: 'Missing required fields for save: type, name, description, content',
              isError: true,
            }
          }

          const memory = await saveMemory({ type, name, description, content })
          return {
            output: `Memory saved successfully. ID: ${memory.id}, Name: ${memory.name}`,
            isError: false,
            metadata: { id: memory.id },
          }
        }

        case 'list': {
          const memories = await listMemories()
          if (memories.length === 0) {
            return { output: 'No memories stored.', isError: false }
          }

          const formatted = memories
            .map((m) => `- [${m.type}] ${m.name} (${m.id}): ${m.description}`)
            .join('\n')
          return {
            output: `${memories.length} memories found:\n${formatted}`,
            isError: false,
            metadata: { count: memories.length },
          }
        }

        case 'search': {
          const query = input.query as string
          if (!query) {
            return { output: 'Missing required field: query', isError: true }
          }

          const results = await searchMemories(query)
          if (results.length === 0) {
            return { output: `No memories found matching "${query}".`, isError: false }
          }

          const formatted = results
            .map((m) => `- [${m.type}] ${m.name} (${m.id}): ${m.description}\n  ${m.content.slice(0, 200)}`)
            .join('\n')
          return {
            output: `${results.length} memories found:\n${formatted}`,
            isError: false,
            metadata: { count: results.length },
          }
        }

        case 'delete': {
          const id = input.id as string
          if (!id) {
            return { output: 'Missing required field: id', isError: true }
          }

          await deleteMemory(id)
          return { output: `Memory ${id} deleted.`, isError: false }
        }

        default:
          return {
            output: `Unknown action: ${action}. Use save, list, search, or delete.`,
            isError: true,
          }
      }
    } catch (err: unknown) {
      return {
        output: `Memory write error: ${err instanceof Error ? err.message : String(err)}`,
        isError: true,
      }
    }
  },
}

// ─── Memory Read Tool ────────────────────────────────────────

export const memoryReadTool: ToolDef = {
  name: 'memory_read',
  description:
    'Read persistent memories — get a specific memory by ID, list all, search by keyword, or get the memory index.',
  inputSchema: {
    type: 'object',
    required: ['action'],
    properties: {
      action: {
        type: 'string',
        enum: ['get', 'list', 'search', 'index'],
        description: 'Action to perform',
      },
      id: {
        type: 'string',
        description: 'Memory ID (required for get)',
      },
      query: {
        type: 'string',
        description: 'Search query (required for search)',
      },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input): Promise<ToolResult> {
    try {
      const action = input.action as string

      switch (action) {
        case 'get': {
          const id = input.id as string
          if (!id) {
            return { output: 'Missing required field: id', isError: true }
          }

          const memory = await getMemory(id)
          if (!memory) {
            return { output: `Memory ${id} not found.`, isError: true }
          }

          return {
            output: `[${memory.type}] ${memory.name}\n${memory.description}\n\n${memory.content}`,
            isError: false,
            metadata: { id: memory.id, type: memory.type },
          }
        }

        case 'list': {
          const memories = await listMemories()
          if (memories.length === 0) {
            return { output: 'No memories stored.', isError: false }
          }

          const formatted = memories
            .map((m) => `- [${m.type}] ${m.name} (${m.id}): ${m.description}`)
            .join('\n')
          return {
            output: `${memories.length} memories found:\n${formatted}`,
            isError: false,
            metadata: { count: memories.length },
          }
        }

        case 'search': {
          const query = input.query as string
          if (!query) {
            return { output: 'Missing required field: query', isError: true }
          }

          const results = await searchMemories(query)
          if (results.length === 0) {
            return { output: `No memories found matching "${query}".`, isError: false }
          }

          const formatted = results
            .map((m) => `- [${m.type}] ${m.name} (${m.id}): ${m.description}\n  ${m.content.slice(0, 200)}`)
            .join('\n')
          return {
            output: `${results.length} memories found:\n${formatted}`,
            isError: false,
            metadata: { count: results.length },
          }
        }

        case 'index': {
          const index = await getMemoryIndex()
          return { output: index, isError: false }
        }

        default:
          return {
            output: `Unknown action: ${action}. Use get, list, search, or index.`,
            isError: true,
          }
      }
    } catch (err: unknown) {
      return {
        output: `Memory read error: ${err instanceof Error ? err.message : String(err)}`,
        isError: true,
      }
    }
  },
}
