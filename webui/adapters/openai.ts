/**
 * OpenAI-compatible model adapter.
 * Works with DeepSeek, MiniMax, OpenAI, Ollama, and any OpenAI-compatible API.
 */
import type {
  ModelAdapter,
  UnifiedChatRequest,
  UnifiedStreamEvent,
  UnifiedMessage,
  UnifiedToolDef,
  ContentBlock,
} from './types.js'
import type { ProviderConfig } from '../config/types.js'
import { convertToolsToOpenAI, convertToolResultsToOpenAI } from './toolMapping.js'
import { unifiedToOpenAIMessages } from './messageNormalizer.js'

export class OpenAICompatibleAdapter implements ModelAdapter {
  readonly providerType: string
  private config: ProviderConfig
  private _supportsTools: boolean

  constructor(config: ProviderConfig, supportsTools = true) {
    this.config = config
    this.providerType = config.type
    this._supportsTools = supportsTools
  }

  supportsToolCalling(): boolean {
    return this._supportsTools
  }
  supportsStreaming(): boolean {
    return true
  }
  supportsThinking(): boolean {
    return false
  }
  supportedModels(): string[] {
    return this.config.models
  }

  async *chat(
    req: UnifiedChatRequest,
    signal?: AbortSignal
  ): AsyncGenerator<UnifiedStreamEvent, void, unknown> {
    const baseUrl = this.config.baseUrl.replace(/\/$/, '')
    const url = `${baseUrl}/chat/completions`

    // Convert messages
    const messages = unifiedToOpenAIMessages(req.messages, req.systemPrompt)

    // If tool calling not supported, inject tool descriptions into system prompt
    if (!this._supportsTools && req.tools && req.tools.length > 0) {
      const toolDesc = this.buildToolDescriptionPrompt(req.tools)
      const sysIdx = messages.findIndex((m) => m.role === 'system')
      if (sysIdx >= 0) {
        messages[sysIdx]!.content += '\n\n' + toolDesc
      } else {
        messages.unshift({ role: 'system', content: toolDesc })
      }
    }

    const body: Record<string, unknown> = {
      model: req.model,
      messages,
      stream: true,
      max_tokens: req.maxTokens || 4096,
    }

    if (req.temperature !== undefined) {
      body.temperature = req.temperature
    }

    // Add tools if supported
    if (this._supportsTools && req.tools && req.tools.length > 0) {
      body.tools = convertToolsToOpenAI(req.tools)
      body.tool_choice = 'auto'
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${this.config.apiKey}`,
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
      yield { type: 'stream_error', error: `API error ${response.status}: ${errorText}` }
      return
    }

    if (!response.body) {
      yield { type: 'stream_error', error: 'No response body' }
      return
    }

    const messageId = crypto.randomUUID()
    yield { type: 'stream_start', messageId }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const toolCalls: Map<number, { id: string; name: string; arguments: string }> = new Map()
    let totalInputTokens = 0
    let totalOutputTokens = 0
    // Track <think> tag state for models that embed thinking in text
    let insideThinkTag = false
    let thinkBuffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') {
            // Finalize any pending tool calls
            for (const [, tc] of toolCalls) {
              let input: Record<string, unknown> = {}
              try {
                input = JSON.parse(tc.arguments)
              } catch {
                // Keep empty
              }
              yield { type: 'stream_tool_use_end', toolId: tc.id, input }
            }
            yield {
              type: 'stream_end',
              stopReason: 'end_turn',
              usage:
                totalInputTokens || totalOutputTokens
                  ? { inputTokens: totalInputTokens, outputTokens: totalOutputTokens }
                  : undefined,
            }
            return
          }

          try {
            const chunk = JSON.parse(data)
            const choice = chunk.choices?.[0]
            const delta = choice?.delta

            // Track usage
            if (chunk.usage) {
              totalInputTokens = chunk.usage.prompt_tokens || 0
              totalOutputTokens = chunk.usage.completion_tokens || 0
            }

            if (!delta) continue

            // Text content — parse <think> tags for models like MiniMax
            if (delta.content) {
              let chunk: string = delta.content
              while (chunk.length > 0) {
                if (insideThinkTag) {
                  const closeIdx = chunk.indexOf('</think>')
                  if (closeIdx !== -1) {
                    // Emit thinking up to close tag
                    const thinkPart = chunk.slice(0, closeIdx)
                    if (thinkPart) yield { type: 'stream_thinking_delta' as const, text: thinkPart }
                    insideThinkTag = false
                    chunk = chunk.slice(closeIdx + 8) // skip '</think>'
                  } else {
                    // Still inside think, emit all as thinking
                    yield { type: 'stream_thinking_delta' as const, text: chunk }
                    chunk = ''
                  }
                } else {
                  const openIdx = chunk.indexOf('<think>')
                  if (openIdx !== -1) {
                    // Emit text before the tag
                    const textPart = chunk.slice(0, openIdx)
                    if (textPart) yield { type: 'stream_text_delta' as const, text: textPart }
                    insideThinkTag = true
                    chunk = chunk.slice(openIdx + 7) // skip '<think>'
                  } else {
                    // No think tag, emit as text
                    yield { type: 'stream_text_delta' as const, text: chunk }
                    chunk = ''
                  }
                }
              }
            }

            // Reasoning/thinking content (DeepSeek R1 style)
            if (delta.reasoning_content) {
              yield { type: 'stream_thinking_delta', text: delta.reasoning_content }
            }

            // Tool calls
            if (delta.tool_calls) {
              for (const tc of delta.tool_calls) {
                const idx = tc.index ?? 0
                if (tc.id) {
                  // New tool call
                  toolCalls.set(idx, { id: tc.id, name: tc.function?.name || '', arguments: '' })
                  yield {
                    type: 'stream_tool_use_start',
                    toolId: tc.id,
                    toolName: tc.function?.name || '',
                  }
                }
                if (tc.function?.arguments) {
                  const existing = toolCalls.get(idx)
                  if (existing) {
                    existing.arguments += tc.function.arguments
                    yield {
                      type: 'stream_tool_use_delta',
                      toolId: existing.id,
                      inputDelta: tc.function.arguments,
                    }
                  }
                }
              }
            }

            // Check finish reason
            if (choice?.finish_reason) {
              // Finalize tool calls if stopped for tool_calls
              if (choice.finish_reason === 'tool_calls' || choice.finish_reason === 'stop') {
                for (const [, tc] of toolCalls) {
                  let input: Record<string, unknown> = {}
                  try {
                    input = JSON.parse(tc.arguments)
                  } catch {
                    // Keep empty
                  }
                  yield { type: 'stream_tool_use_end', toolId: tc.id, input }
                }
                toolCalls.clear()
              }
              yield {
                type: 'stream_end',
                stopReason:
                  choice.finish_reason === 'tool_calls' ? 'tool_use' : choice.finish_reason,
                usage:
                  totalInputTokens || totalOutputTokens
                    ? { inputTokens: totalInputTokens, outputTokens: totalOutputTokens }
                    : undefined,
              }
            }
          } catch {
            // Skip malformed chunks
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  /**
   * For models without function calling: inject tool descriptions as text.
   */
  private buildToolDescriptionPrompt(tools: UnifiedToolDef[]): string {
    let prompt = `You have access to the following tools. To use a tool, respond with a JSON block in this format:
\`\`\`tool_call
{"name": "tool_name", "arguments": {"param1": "value1"}}
\`\`\`

Available tools:\n\n`

    for (const tool of tools) {
      prompt += `### ${tool.name}\n${tool.description}\nParameters: ${JSON.stringify(tool.inputSchema, null, 2)}\n\n`
    }

    return prompt
  }
}
