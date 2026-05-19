/**
 * WebSocket message protocol types for client-server communication.
 */

// ─── Client → Server Messages ─────────────────────────────────

export interface ClientUserMessage {
  type: 'user_message'
  content: string
  sessionId?: string
  mode?: string
  model?: string
  provider?: string
  attachments?: Array<{
    type: 'image' | 'file'
    name: string
    data: string // base64
    mimeType: string
  }>
}

export interface ClientPermissionResponse {
  type: 'permission_response'
  toolUseId: string
  allowed: boolean
}

export interface ClientAbort {
  type: 'abort'
}

export interface ClientPing {
  type: 'ping'
}

export interface ClientSwitchModel {
  type: 'switch_model'
  model: string
  provider: string
}

export type ClientMessage =
  | ClientUserMessage
  | ClientPermissionResponse
  | ClientAbort
  | ClientSwitchModel
  | ClientPing

// ─── Server → Client Messages ─────────────────────────────────

export interface ServerStreamStart {
  type: 'stream_start'
  messageId: string
  sessionId: string
  model: string
  provider: string
}

export interface ServerStreamDelta {
  type: 'stream_delta'
  contentType: 'text' | 'thinking'
  text: string
}

export interface ServerToolUseStart {
  type: 'tool_use_start'
  toolId: string
  toolName: string
  input: Record<string, unknown>
}

export interface ServerToolResult {
  type: 'tool_result'
  toolId: string
  toolName: string
  output: string
  isError: boolean
}

export interface ServerPermissionRequest {
  type: 'permission_request'
  toolName: string
  toolId: string
  input: Record<string, unknown>
  description: string
}

export interface ServerStreamEnd {
  type: 'stream_end'
  usage?: {
    inputTokens: number
    outputTokens: number
  }
  stopReason?: string
}

export interface ServerError {
  type: 'error'
  message: string
  code?: string
}

export interface ServerSessionInfo {
  type: 'session_info'
  sessionId: string
  model: string
  provider: string
}

export interface ServerModelSwitched {
  type: 'model_switched'
  model: string
  provider: string
}

export interface ServerPong {
  type: 'pong'
}

export interface ServerTitleUpdated {
  type: 'title_updated'
  sessionId: string
  title: string
}

export type ServerMessage =
  | ServerStreamStart
  | ServerStreamDelta
  | ServerToolUseStart
  | ServerToolResult
  | ServerPermissionRequest
  | ServerStreamEnd
  | ServerError
  | ServerSessionInfo
  | ServerModelSwitched
  | ServerPong
  | ServerTitleUpdated
