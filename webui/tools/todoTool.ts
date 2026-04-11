/**
 * TODO/Task Tracking Tool — manages per-session task lists.
 * Tasks are stored in memory, keyed by session ID.
 */
import type { ToolDef, ToolResult } from './types.js'

// ─── Task Types ──────────────────────────────────────────────

interface Task {
  id: string
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

interface TodoInput {
  action: 'create' | 'update' | 'list' | 'clear'
  sessionId: string
  tasks?: Task[]
}

// ─── Per-Session Storage ─────────────────────────────────────

const sessionTodos = new Map<string, Task[]>()

export function getSessionTodos(sessionId: string): Task[] {
  return sessionTodos.get(sessionId) || []
}

export function setSessionTodos(sessionId: string, todos: Task[]): void {
  sessionTodos.set(sessionId, todos)
}

// ─── Tool Definition ─────────────────────────────────────────

export const todoWriteTool: ToolDef = {
  name: 'todo_write',
  description:
    'Manage a task list for the current session. Actions: create (add tasks), update (modify tasks by id), list (show all tasks), clear (remove all tasks). Tasks have id, content, and status (pending | in_progress | completed).',
  inputSchema: {
    type: 'object',
    required: ['action', 'sessionId'],
    properties: {
      action: {
        type: 'string',
        enum: ['create', 'update', 'list', 'clear'],
        description: 'Action to perform on the task list',
      },
      sessionId: {
        type: 'string',
        description: 'Session ID to scope the task list',
      },
      tasks: {
        type: 'array',
        description: 'Tasks to create or update (required for create/update)',
        items: {
          type: 'object',
          required: ['id', 'content', 'status'],
          properties: {
            id: { type: 'string', description: 'Unique task identifier' },
            content: { type: 'string', description: 'Task description' },
            status: {
              type: 'string',
              enum: ['pending', 'in_progress', 'completed'],
              description: 'Task status',
            },
          },
        },
      },
    },
  },
  isReadOnly: false,
  riskLevel: 'low',

  async execute(input): Promise<ToolResult> {
    try {
      const { action, sessionId, tasks } = input as unknown as TodoInput

      if (!sessionId) {
        return { output: 'sessionId is required.', isError: true }
      }

      switch (action) {
        case 'create': {
          if (!tasks || tasks.length === 0) {
            return { output: 'tasks array is required for create action.', isError: true }
          }
          const existing = getSessionTodos(sessionId)
          const merged = [...existing, ...tasks]
          setSessionTodos(sessionId, merged)
          return {
            output: `Created ${tasks.length} task(s). Total: ${merged.length}.`,
            isError: false,
            metadata: { count: merged.length },
          }
        }

        case 'update': {
          if (!tasks || tasks.length === 0) {
            return { output: 'tasks array is required for update action.', isError: true }
          }
          const current = getSessionTodos(sessionId)
          const updateMap = new Map(tasks.map((t) => [t.id, t]))
          const updated = current.map((t) => updateMap.get(t.id) || t)
          // Add any tasks with new IDs
          for (const t of tasks) {
            if (!current.some((c) => c.id === t.id)) {
              updated.push(t)
            }
          }
          setSessionTodos(sessionId, updated)
          return {
            output: `Updated ${tasks.length} task(s). Total: ${updated.length}.`,
            isError: false,
            metadata: { count: updated.length },
          }
        }

        case 'list': {
          const all = getSessionTodos(sessionId)
          if (all.length === 0) {
            return { output: 'No tasks found for this session.', isError: false, metadata: { count: 0 } }
          }
          const lines = all.map(
            (t) => `[${t.status}] ${t.id}: ${t.content}`
          )
          return {
            output: lines.join('\n'),
            isError: false,
            metadata: { count: all.length },
          }
        }

        case 'clear': {
          const prev = getSessionTodos(sessionId).length
          setSessionTodos(sessionId, [])
          return {
            output: `Cleared ${prev} task(s) from session.`,
            isError: false,
            metadata: { cleared: prev },
          }
        }

        default:
          return { output: `Unknown action: ${action}. Use create, update, list, or clear.`, isError: true }
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
