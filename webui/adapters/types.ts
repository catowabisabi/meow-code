/**
 * Unified multi-model adapter types.
 * All model providers (Anthropic, DeepSeek, MiniMax, Ollama, etc.)
 * are abstracted behind these interfaces.
 */

// ─── Content Blocks ───────────────────────────────────────────

export interface TextBlock {
  type: 'text'
  text: string
}

export interface ThinkingBlock {
  type: 'thinking'
  text: string
}

export interface ToolUseBlock {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
}

export interface ToolResultBlock {
  type: 'tool_result'
  tool_use_id: string
  content: string
  is_error?: boolean
}

export interface ImageBlock {
  type: 'image'
  source: {
    type: 'base64'
    media_type: string
    data: string
  }
}

export type ContentBlock =
  | TextBlock
  | ThinkingBlock
  | ToolUseBlock
  | ToolResultBlock
  | ImageBlock

// ─── Messages ─────────────────────────────────────────────────

export interface UnifiedMessage {
  role: 'user' | 'assistant' | 'system'
  content: ContentBlock[] | string
}

// ─── Tool Definitions ─────────────────────────────────────────

export interface UnifiedToolDef {
  name: string
  description: string
  inputSchema: Record<string, unknown>
}

// ─── Requests ─────────────────────────────────────────────────

export interface UnifiedChatRequest {
  messages: UnifiedMessage[]
  model: string
  provider: string
  systemPrompt?: string
  tools?: UnifiedToolDef[]
  stream: boolean
  maxTokens?: number
  temperature?: number
  thinkingEnabled?: boolean
}

// ─── Stream Events ────────────────────────────────────────────

export interface StreamStartEvent {
  type: 'stream_start'
  messageId: string
}

export interface StreamTextDeltaEvent {
  type: 'stream_text_delta'
  text: string
}

export interface StreamThinkingDeltaEvent {
  type: 'stream_thinking_delta'
  text: string
}

export interface StreamToolUseStartEvent {
  type: 'stream_tool_use_start'
  toolId: string
  toolName: string
}

export interface StreamToolUseDeltaEvent {
  type: 'stream_tool_use_delta'
  toolId: string
  inputDelta: string
}

export interface StreamToolUseEndEvent {
  type: 'stream_tool_use_end'
  toolId: string
  input: Record<string, unknown>
}

export interface StreamEndEvent {
  type: 'stream_end'
  usage?: {
    inputTokens: number
    outputTokens: number
  }
  stopReason?: string
}

export interface StreamErrorEvent {
  type: 'stream_error'
  error: string
}

export type UnifiedStreamEvent =
  | StreamStartEvent
  | StreamTextDeltaEvent
  | StreamThinkingDeltaEvent
  | StreamToolUseStartEvent
  | StreamToolUseDeltaEvent
  | StreamToolUseEndEvent
  | StreamEndEvent
  | StreamErrorEvent

// ─── Adapter Interface ────────────────────────────────────────

export interface ModelAdapter {
  readonly providerType: string

  chat(
    req: UnifiedChatRequest,
    signal?: AbortSignal
  ): AsyncGenerator<UnifiedStreamEvent, void, unknown>

  supportsToolCalling(): boolean
  supportsStreaming(): boolean
  supportsThinking(): boolean
  supportedModels(): string[]
}

// ─── Provider Capabilities ────────────────────────────────────

export interface ProviderCapabilities {
  toolCalling: boolean
  streaming: boolean
  thinking: boolean
  vision: boolean
}

export const KNOWN_PROVIDERS: Record<
  string,
  { displayName: string; defaultBaseUrl: string; capabilities: ProviderCapabilities }
> = {
  anthropic: {
    displayName: 'Anthropic (Claude)',
    defaultBaseUrl: 'https://api.anthropic.com',
    capabilities: { toolCalling: true, streaming: true, thinking: true, vision: true },
  },
  deepseek: {
    displayName: 'DeepSeek',
    defaultBaseUrl: 'https://api.deepseek.com/v1',
    capabilities: { toolCalling: true, streaming: true, thinking: false, vision: false },
  },
  minimax: {
    displayName: 'MiniMax',
    defaultBaseUrl: 'https://api.minimax.io/v1',
    capabilities: { toolCalling: true, streaming: true, thinking: false, vision: false },
  },
  openai: {
    displayName: 'OpenAI',
    defaultBaseUrl: 'https://api.openai.com/v1',
    capabilities: { toolCalling: true, streaming: true, thinking: false, vision: true },
  },
  ollama: {
    displayName: 'Ollama (Local)',
    defaultBaseUrl: 'http://localhost:11434/v1',
    capabilities: { toolCalling: false, streaming: true, thinking: false, vision: false },
  },
  'openai-compatible': {
    displayName: 'OpenAI Compatible',
    defaultBaseUrl: '',
    capabilities: { toolCalling: true, streaming: true, thinking: false, vision: false },
  },
}
