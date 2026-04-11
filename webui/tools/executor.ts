/**
 * Tool Executor Engine — the heart of the agentic loop.
 *
 * Manages tool registration, concurrent execution, and orchestration.
 * Mirrors the original toolOrchestration.ts pattern:
 *   - Read-only tools run concurrently (max 10)
 *   - Write tools run serially
 */
import type { ToolDef, ToolContext, ToolResult, ToolCall, ToolCallResult, ToolProgress } from './types.js'
import { shellTool } from './shellTool.js'
import { fileReadTool, fileWriteTool, fileEditTool, globTool, grepTool } from './fileTools.js'
import { webFetchTool, webSearchTool } from './webTools.js'
import { todoWriteTool } from './todoTool.js'
import { enterPlanModeTool, exitPlanModeTool } from './planTool.js'
import { memoryWriteTool, memoryReadTool } from './memoryTool.js'
import { agentSpawnTool, agentStatusTool } from './agentTool.js'
import { notionSearchTool, notionReadPageTool, notionWritePageTool, notionDatabaseTool, notionBlockTool } from './notionTools.js'
import { databaseTool } from './databaseTool.js'
import { reportGenerateTool } from './reportTool.js'

// ─── Tool Registry ────────────────────────────────────────────

const toolRegistry = new Map<string, ToolDef>()

function registerTool(tool: ToolDef) {
  toolRegistry.set(tool.name, tool)
}

// Register all built-in tools
registerTool(shellTool)
registerTool(fileReadTool)
registerTool(fileWriteTool)
registerTool(fileEditTool)
registerTool(globTool)
registerTool(grepTool)
registerTool(webFetchTool)
registerTool(webSearchTool)
registerTool(todoWriteTool)
registerTool(enterPlanModeTool)
registerTool(exitPlanModeTool)
registerTool(memoryWriteTool)
registerTool(memoryReadTool)
registerTool(agentSpawnTool)
registerTool(agentStatusTool)
registerTool(notionSearchTool)
registerTool(notionReadPageTool)
registerTool(notionWritePageTool)
registerTool(notionDatabaseTool)
registerTool(notionBlockTool)
registerTool(databaseTool)
registerTool(reportGenerateTool)

export function getAllTools(): ToolDef[] {
  return Array.from(toolRegistry.values())
}

export function getTool(name: string): ToolDef | undefined {
  return toolRegistry.get(name)
}

// ─── Tool Schemas for AI ──────────────────────────────────────

/** Get all tool definitions in OpenAI function-calling format */
export function getToolSchemasForAI(): Array<{
  type: 'function'
  function: { name: string; description: string; parameters: Record<string, unknown> }
}> {
  return getAllTools().map((t) => ({
    type: 'function' as const,
    function: {
      name: t.name,
      description: t.description,
      parameters: t.inputSchema,
    },
  }))
}

/** Get all tool definitions in Anthropic format */
export function getToolSchemasForAnthropic(): Array<{
  name: string
  description: string
  input_schema: Record<string, unknown>
}> {
  return getAllTools().map((t) => ({
    name: t.name,
    description: t.description,
    input_schema: t.inputSchema,
  }))
}

// ─── Single Tool Execution ────────────────────────────────────

export async function executeTool(
  toolCall: ToolCall,
  ctx: ToolContext,
  onEvent?: (event: ToolExecutionEvent) => void,
): Promise<ToolCallResult> {
  const tool = getTool(toolCall.name)

  if (!tool) {
    return {
      tool_call_id: toolCall.id,
      name: toolCall.name,
      output: `Unknown tool: ${toolCall.name}. Available tools: ${getAllTools().map((t) => t.name).join(', ')}`,
      isError: true,
    }
  }

  onEvent?.({
    type: 'tool_start',
    toolId: toolCall.id,
    toolName: toolCall.name,
    input: toolCall.arguments,
  })

  // Permission check for high-risk tools
  if (tool.riskLevel === 'high' && ctx.requestPermission) {
    const description = `Execute ${tool.name}: ${JSON.stringify(toolCall.arguments).slice(0, 200)}`
    const allowed = await ctx.requestPermission(tool.name, toolCall.arguments, description)
    if (!allowed) {
      const result: ToolCallResult = {
        tool_call_id: toolCall.id,
        name: toolCall.name,
        output: 'Permission denied by user.',
        isError: true,
      }
      onEvent?.({ type: 'tool_end', toolId: toolCall.id, toolName: toolCall.name, result })
      return result
    }
  }

  try {
    // Execute with progress tracking
    const toolResult = await tool.execute(toolCall.arguments, {
      ...ctx,
      onProgress: (progress) => {
        progress.toolId = toolCall.id
        onEvent?.({ type: 'tool_progress', toolId: toolCall.id, toolName: toolCall.name, progress })
      },
    })

    const result: ToolCallResult = {
      tool_call_id: toolCall.id,
      name: toolCall.name,
      output: toolResult.output,
      isError: toolResult.isError,
    }

    onEvent?.({ type: 'tool_end', toolId: toolCall.id, toolName: toolCall.name, result })
    return result
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err)
    const result: ToolCallResult = {
      tool_call_id: toolCall.id,
      name: toolCall.name,
      output: `Tool execution error: ${errMsg}`,
      isError: true,
    }
    onEvent?.({ type: 'tool_end', toolId: toolCall.id, toolName: toolCall.name, result })
    return result
  }
}

// ─── Orchestrated Multi-Tool Execution ────────────────────────

/**
 * Execute multiple tool calls with smart concurrency:
 * - Read-only tools run in parallel (max concurrency: 10)
 * - Write tools run one at a time, serially
 */
export async function executeToolCalls(
  toolCalls: ToolCall[],
  ctx: ToolContext,
  onEvent?: (event: ToolExecutionEvent) => void,
): Promise<ToolCallResult[]> {
  const MAX_CONCURRENT = 10

  // Partition into read-only and write tools
  const readCalls: ToolCall[] = []
  const writeCalls: ToolCall[] = []

  for (const tc of toolCalls) {
    const tool = getTool(tc.name)
    if (tool?.isReadOnly) {
      readCalls.push(tc)
    } else {
      writeCalls.push(tc)
    }
  }

  const results: ToolCallResult[] = []

  // Run read-only tools concurrently (batched by MAX_CONCURRENT)
  for (let i = 0; i < readCalls.length; i += MAX_CONCURRENT) {
    const batch = readCalls.slice(i, i + MAX_CONCURRENT)
    const batchResults = await Promise.all(
      batch.map((tc) => executeTool(tc, ctx, onEvent))
    )
    results.push(...batchResults)
  }

  // Run write tools serially
  for (const tc of writeCalls) {
    const result = await executeTool(tc, ctx, onEvent)
    results.push(result)
  }

  return results
}

// ─── Event Types ──────────────────────────────────────────────

export type ToolExecutionEvent =
  | { type: 'tool_start'; toolId: string; toolName: string; input: Record<string, unknown> }
  | { type: 'tool_progress'; toolId: string; toolName: string; progress: ToolProgress }
  | { type: 'tool_end'; toolId: string; toolName: string; result: ToolCallResult }
  | { type: 'permission_request'; toolId: string; toolName: string; input: Record<string, unknown>; description: string }
