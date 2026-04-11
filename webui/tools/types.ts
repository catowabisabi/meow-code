/**
 * Tool system types for WebUI.
 * Each tool has a schema, execution function, and metadata.
 */

export interface ToolDef {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  /** Whether this tool modifies state (affects concurrency) */
  isReadOnly: boolean
  /** Risk level for permission system */
  riskLevel: 'low' | 'medium' | 'high'
  /** Execute the tool */
  execute: (input: Record<string, unknown>, ctx: ToolContext) => Promise<ToolResult>
}

export interface ToolContext {
  cwd: string
  abortSignal?: AbortSignal
  onProgress?: (data: ToolProgress) => void
  /** Permission callback: returns true if user approves */
  requestPermission?: (tool: string, input: Record<string, unknown>, description: string) => Promise<boolean>
}

export interface ToolResult {
  output: string
  isError: boolean
  metadata?: Record<string, unknown>
}

export interface ToolProgress {
  toolName: string
  toolId: string
  type: 'stdout' | 'stderr' | 'status'
  data: string
}

/** Tool use block from AI response (OpenAI format) */
export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
}

/** Tool result to feed back to AI */
export interface ToolCallResult {
  tool_call_id: string
  name: string
  output: string
  isError: boolean
}
