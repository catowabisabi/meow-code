/**
 * Convert messages between Unified format and OpenAI format.
 */
import type { UnifiedMessage, ContentBlock } from './types.js'

// ─── OpenAI Message Types ─────────────────────────────────────

export interface OpenAIMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string | null
  tool_calls?: Array<{
    id: string
    type: 'function'
    function: { name: string; arguments: string }
  }>
  tool_call_id?: string
}

// ─── Unified → OpenAI ─────────────────────────────────────────

export function unifiedToOpenAIMessages(
  messages: UnifiedMessage[],
  systemPrompt?: string
): OpenAIMessage[] {
  const result: OpenAIMessage[] = []

  // Add system prompt first
  if (systemPrompt) {
    result.push({ role: 'system', content: systemPrompt })
  }

  for (const msg of messages) {
    if (msg.role === 'system') {
      result.push({ role: 'system', content: extractText(msg.content) })
      continue
    }

    if (msg.role === 'user') {
      const userMsgs = convertUserMessage(msg)
      result.push(...userMsgs)
      continue
    }

    if (msg.role === 'assistant') {
      const assistantMsgs = convertAssistantMessage(msg)
      result.push(...assistantMsgs)
      continue
    }
  }

  return result
}

function convertUserMessage(msg: UnifiedMessage): OpenAIMessage[] {
  if (typeof msg.content === 'string') {
    return [{ role: 'user', content: msg.content }]
  }

  const results: OpenAIMessage[] = []
  const textParts: string[] = []
  const toolResults: Array<{ tool_call_id: string; content: string }> = []

  for (const block of msg.content) {
    switch (block.type) {
      case 'text':
        textParts.push(block.text)
        break
      case 'tool_result':
        toolResults.push({
          tool_call_id: block.tool_use_id,
          content: typeof block.content === 'string' ? block.content : JSON.stringify(block.content),
        })
        break
      case 'image':
        // OpenAI vision format
        textParts.push('[Image attached]')
        break
    }
  }

  // Tool results go as separate 'tool' messages
  for (const tr of toolResults) {
    results.push({
      role: 'tool',
      content: tr.content,
      tool_call_id: tr.tool_call_id,
    })
  }

  // Regular text as user message
  if (textParts.length > 0) {
    results.push({ role: 'user', content: textParts.join('\n') })
  }

  return results
}

function convertAssistantMessage(msg: UnifiedMessage): OpenAIMessage[] {
  if (typeof msg.content === 'string') {
    return [{ role: 'assistant', content: msg.content }]
  }

  const textParts: string[] = []
  const toolCalls: Array<{
    id: string
    type: 'function'
    function: { name: string; arguments: string }
  }> = []

  for (const block of msg.content) {
    switch (block.type) {
      case 'text':
        textParts.push(block.text)
        break
      case 'thinking':
        // Include thinking as text prefix
        textParts.push(`<thinking>${block.text}</thinking>`)
        break
      case 'tool_use':
        toolCalls.push({
          id: block.id,
          type: 'function',
          function: {
            name: block.name,
            arguments: JSON.stringify(block.input),
          },
        })
        break
    }
  }

  const result: OpenAIMessage = {
    role: 'assistant',
    content: textParts.length > 0 ? textParts.join('\n') : null,
  }

  if (toolCalls.length > 0) {
    result.tool_calls = toolCalls
  }

  return [result]
}

// ─── OpenAI → Unified ─────────────────────────────────────────

export function openAIToUnifiedMessages(messages: OpenAIMessage[]): UnifiedMessage[] {
  return messages.map((msg) => {
    if (msg.role === 'tool') {
      return {
        role: 'user' as const,
        content: [
          {
            type: 'tool_result' as const,
            tool_use_id: msg.tool_call_id || '',
            content: msg.content || '',
          },
        ],
      }
    }

    if (msg.role === 'assistant' && msg.tool_calls) {
      const blocks: ContentBlock[] = []
      if (msg.content) {
        blocks.push({ type: 'text', text: msg.content })
      }
      for (const tc of msg.tool_calls) {
        let input: Record<string, unknown> = {}
        try {
          input = JSON.parse(tc.function.arguments)
        } catch {
          // Keep empty
        }
        blocks.push({
          type: 'tool_use',
          id: tc.id,
          name: tc.function.name,
          input,
        })
      }
      return { role: 'assistant' as const, content: blocks }
    }

    return {
      role: msg.role === 'system' ? ('system' as const) : (msg.role as 'user' | 'assistant'),
      content: msg.content || '',
    }
  })
}

// ─── Helpers ──────────────────────────────────────────────────

function extractText(content: string | ContentBlock[]): string {
  if (typeof content === 'string') return content
  return content
    .filter((b): b is { type: 'text'; text: string } => b.type === 'text')
    .map((b) => b.text)
    .join('\n')
}
