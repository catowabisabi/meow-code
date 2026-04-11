/**
 * Plan Mode Tools — switch sessions between execution and planning mode.
 *
 * When plan mode is active:
 *  - Only read-only tools are available (file_read, glob, grep, web_fetch, web_search)
 *  - System prompt gets a PLAN MODE prefix instructing the AI to explore and plan only
 */
import type { ToolDef, ToolResult } from './types.js'

// ─── Per-Session Plan Mode State ─────────────────────────────

const planModeState = new Map<string, boolean>()

export function isPlanMode(sessionId: string): boolean {
  return planModeState.get(sessionId) === true
}

export function setPlanMode(sessionId: string, active: boolean): void {
  planModeState.set(sessionId, active)
}

// ─── Plan Mode System Prompt Prefix ──────────────────────────

export function getPlanModeSystemPromptPrefix(): string {
  return `## PLAN MODE ACTIVE

You are currently in PLAN MODE. In this mode:

1. **DO NOT** modify any files, run destructive commands, or make changes to the codebase.
2. **ONLY** use read-only tools: file_read, glob, grep, web_fetch, web_search.
3. **Focus on**: exploring the codebase, understanding architecture, gathering information, and formulating a plan.
4. **Output**: a clear, step-by-step plan of what changes need to be made, why, and in what order.
5. **Ask questions** if anything is unclear before the user exits plan mode and you begin execution.

Think carefully. Explore thoroughly. Plan before you act.

---

`
}

// ─── Read-only tool whitelist ────────────────────────────────

const READ_ONLY_TOOLS = new Set([
  'file_read',
  'glob',
  'grep',
  'web_fetch',
  'web_search',
  'enter_plan_mode',
  'exit_plan_mode',
  'todo_write',
])

export function isToolAllowedInPlanMode(toolName: string): boolean {
  return READ_ONLY_TOOLS.has(toolName)
}

// ─── Enter Plan Mode Tool ────────────────────────────────────

export const enterPlanModeTool: ToolDef = {
  name: 'enter_plan_mode',
  description:
    'Switch the current session to plan mode. In plan mode, only read-only tools are available and the AI focuses on exploration and planning rather than making changes.',
  inputSchema: {
    type: 'object',
    required: ['sessionId'],
    properties: {
      sessionId: {
        type: 'string',
        description: 'Session ID to switch to plan mode',
      },
    },
  },
  isReadOnly: false,
  riskLevel: 'low',

  async execute(input): Promise<ToolResult> {
    try {
      const sessionId = input.sessionId as string
      if (!sessionId) {
        return { output: 'sessionId is required.', isError: true }
      }

      if (isPlanMode(sessionId)) {
        return { output: 'Already in plan mode.', isError: false }
      }

      setPlanMode(sessionId, true)
      return {
        output: 'Entered plan mode. Only read-only tools are now available. Focus on exploring and planning.',
        isError: false,
        metadata: { planMode: true },
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Exit Plan Mode Tool ─────────────────────────────────────

export const exitPlanModeTool: ToolDef = {
  name: 'exit_plan_mode',
  description:
    'Exit plan mode and return to normal execution mode where all tools are available.',
  inputSchema: {
    type: 'object',
    required: ['sessionId'],
    properties: {
      sessionId: {
        type: 'string',
        description: 'Session ID to exit plan mode',
      },
    },
  },
  isReadOnly: false,
  riskLevel: 'low',

  async execute(input): Promise<ToolResult> {
    try {
      const sessionId = input.sessionId as string
      if (!sessionId) {
        return { output: 'sessionId is required.', isError: true }
      }

      if (!isPlanMode(sessionId)) {
        return { output: 'Not currently in plan mode.', isError: false }
      }

      setPlanMode(sessionId, false)
      return {
        output: 'Exited plan mode. All tools are now available. Ready to execute.',
        isError: false,
        metadata: { planMode: false },
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
