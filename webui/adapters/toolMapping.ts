/**
 * Convert tool definitions between Anthropic and OpenAI formats.
 */
import type { UnifiedToolDef } from './types.js'

// ─── To OpenAI Format ─────────────────────────────────────────

export interface OpenAITool {
  type: 'function'
  function: {
    name: string
    description: string
    parameters: Record<string, unknown>
  }
}

export function convertToolsToOpenAI(tools: UnifiedToolDef[]): OpenAITool[] {
  return tools.map((t) => ({
    type: 'function' as const,
    function: {
      name: t.name,
      description: t.description,
      parameters: t.inputSchema,
    },
  }))
}

// ─── Tool Results for OpenAI ──────────────────────────────────

export interface OpenAIToolResultMessage {
  role: 'tool'
  tool_call_id: string
  content: string
}

export function convertToolResultsToOpenAI(
  toolResults: Array<{ toolUseId: string; content: string; isError?: boolean }>
): OpenAIToolResultMessage[] {
  return toolResults.map((r) => ({
    role: 'tool' as const,
    tool_call_id: r.toolUseId,
    content: r.isError ? `Error: ${r.content}` : r.content,
  }))
}

// ─── Parse Tool Calls from Plain Text (for models without function calling) ───

export interface ParsedToolCall {
  name: string
  arguments: Record<string, unknown>
}

/**
 * Parse tool_call blocks from model response text.
 * Used for models that don't support native function calling.
 */
export function parseToolCallsFromText(text: string): ParsedToolCall[] {
  const results: ParsedToolCall[] = []
  const regex = /```tool_call\s*\n([\s\S]*?)```/g
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    try {
      const parsed = JSON.parse(match[1]!.trim())
      if (parsed.name && parsed.arguments) {
        results.push({
          name: parsed.name,
          arguments: parsed.arguments,
        })
      }
    } catch {
      // Skip malformed tool calls
    }
  }

  return results
}
