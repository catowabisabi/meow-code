/**
 * Anthropic (Claude) model adapter.
 * Calls the Anthropic API directly using fetch for streaming.
 */
import type {
  ModelAdapter,
  UnifiedChatRequest,
  UnifiedStreamEvent,
  UnifiedMessage,
  ContentBlock,
} from './types.js'
import type { ProviderConfig } from '../config/types.js'

export class AnthropicAdapter implements ModelAdapter {
  readonly providerType = 'anthropic'
  private config: ProviderConfig

  constructor(config: ProviderConfig) {
    this.config = config
  }

  supportsToolCalling(): boolean {
    return true
  }
  supportsStreaming(): boolean {
    return true
  }
  supportsThinking(): boolean {
    return true
  }
  supportedModels(): string[] {
    return this.config.models
  }

  async *chat(
    req: UnifiedChatRequest,
    signal?: AbortSignal
  ): AsyncGenerator<UnifiedStreamEvent, void, unknown> {
    const baseUrl = this.config.baseUrl || 'https://api.anthropic.com'
    const url = `${baseUrl}/v1/messages`

    // Convert unified messages to Anthropic format
    const messages = this.convertMessages(req.messages)

    // Build tools in Anthropic format
    const tools = req.tools?.map((t) => ({
      name: t.name,
      description: t.description,
      input_schema: t.inputSchema,
    }))

    const body: Record<string, unknown> = {
      model: req.model,
      max_tokens: req.maxTokens || 8192,
      messages,
      stream: true,
    }

    if (req.systemPrompt) {
      body.system = req.systemPrompt
    }
    if (tools && tools.length > 0) {
      body.tools = tools
    }
    if (req.temperature !== undefined) {
      body.temperature = req.temperature
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-api-key': this.config.apiKey,
      'anthropic-version': '2023-06-01',
      ...this.config.customHeaders,
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    })

    if (!response.ok) {
      const errorText = await response.text()
      yield { type: 'stream_error', error: `Anthropic API error ${response.status}: ${errorText}` }
      return
    }

    if (!response.body) {
      yield { type: 'stream_error', error: 'No response body' }
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let messageId = ''
    let currentToolId = ''
    let currentToolName = ''
    let toolInputBuffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') continue

            try {
              const event = JSON.parse(data)
              yield* this.handleSSEEvent(event, {
                messageId,
                currentToolId,
                currentToolName,
                toolInputBuffer,
                setMessageId: (id: string) => { messageId = id },
                setToolState: (id: string, name: string, input: string) => {
                  currentToolId = id
                  currentToolName = name
                  toolInputBuffer = input
                },
              })
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  private *handleSSEEvent(
    event: Record<string, unknown>,
    state: {
      messageId: string
      currentToolId: string
      currentToolName: string
      toolInputBuffer: string
      setMessageId: (id: string) => void
      setToolState: (id: string, name: string, input: string) => void
    }
  ): Generator<UnifiedStreamEvent> {
    const eventType = event.type as string

    switch (eventType) {
      case 'message_start': {
        const msg = event.message as Record<string, unknown>
        const id = (msg?.id as string) || crypto.randomUUID()
        state.setMessageId(id)
        yield { type: 'stream_start', messageId: id }
        break
      }
      case 'content_block_start': {
        const block = event.content_block as Record<string, unknown>
        if (block?.type === 'tool_use') {
          const toolId = block.id as string
          const toolName = block.name as string
          state.setToolState(toolId, toolName, '')
          yield { type: 'stream_tool_use_start', toolId, toolName }
        }
        break
      }
      case 'content_block_delta': {
        const delta = event.delta as Record<string, unknown>
        if (delta?.type === 'text_delta') {
          yield { type: 'stream_text_delta', text: delta.text as string }
        } else if (delta?.type === 'thinking_delta') {
          yield { type: 'stream_thinking_delta', text: delta.thinking as string }
        } else if (delta?.type === 'input_json_delta') {
          const partial = delta.partial_json as string
          state.setToolState(state.currentToolId, state.currentToolName, state.toolInputBuffer + partial)
          yield { type: 'stream_tool_use_delta', toolId: state.currentToolId, inputDelta: partial }
        }
        break
      }
      case 'content_block_stop': {
        if (state.currentToolId) {
          let input: Record<string, unknown> = {}
          try {
            input = JSON.parse(state.toolInputBuffer)
          } catch {
            // Keep empty
          }
          yield { type: 'stream_tool_use_end', toolId: state.currentToolId, input }
          state.setToolState('', '', '')
        }
        break
      }
      case 'message_delta': {
        const delta = event.delta as Record<string, unknown>
        const usage = event.usage as Record<string, number> | undefined
        if (delta?.stop_reason) {
          yield {
            type: 'stream_end',
            stopReason: delta.stop_reason as string,
            usage: usage
              ? { inputTokens: usage.input_tokens || 0, outputTokens: usage.output_tokens || 0 }
              : undefined,
          }
        }
        break
      }
      case 'message_stop': {
        // Final stop - already handled by message_delta
        break
      }
      case 'error': {
        const err = event.error as Record<string, unknown>
        yield { type: 'stream_error', error: (err?.message as string) || 'Unknown Anthropic error' }
        break
      }
    }
  }

  private convertMessages(messages: UnifiedMessage[]): Array<Record<string, unknown>> {
    return messages
      .filter((m) => m.role !== 'system')
      .map((m) => ({
        role: m.role,
        content:
          typeof m.content === 'string'
            ? m.content
            : (m.content as ContentBlock[]).map((block) => this.convertBlock(block)),
      }))
  }

  private convertBlock(block: ContentBlock): Record<string, unknown> {
    switch (block.type) {
      case 'text':
        return { type: 'text', text: block.text }
      case 'tool_use':
        return { type: 'tool_use', id: block.id, name: block.name, input: block.input }
      case 'tool_result':
        return {
          type: 'tool_result',
          tool_use_id: block.tool_use_id,
          content: block.content,
          is_error: block.is_error,
        }
      case 'image':
        return { type: 'image', source: block.source }
      case 'thinking':
        return { type: 'thinking', thinking: block.text }
      default:
        return { type: 'text', text: '' }
    }
  }
}
