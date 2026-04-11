/**
 * Context Compression Service.
 * Compresses conversation history when it gets too long.
 * Strategy: Keep system prompt + last N messages, summarize the rest.
 */
import type { UnifiedMessage, ContentBlock, TextBlock } from '../adapters/types.js'

export interface CompactResult {
  compactedMessages: UnifiedMessage[]
  summary: string
  originalCount: number
  compactedCount: number
}

/**
 * Check whether compaction is needed based on message count.
 */
export function shouldCompact(messages: UnifiedMessage[], threshold: number = 40): boolean {
  return messages.length > threshold
}

/**
 * Extract plain text from a message's content blocks.
 */
function extractText(content: ContentBlock[] | string): string {
  if (typeof content === 'string') return content
  return content
    .filter((b): b is TextBlock => b.type === 'text')
    .map((b) => b.text)
    .join(' ')
}

/**
 * Build a human-readable summary from a list of messages.
 * Extracts key decisions, file paths mentioned, and task progress.
 */
export function buildSummary(messages: UnifiedMessage[]): string {
  const parts: string[] = []
  const filePaths = new Set<string>()
  const decisions: string[] = []

  for (const msg of messages) {
    const text = extractText(msg.content)
    if (!text) continue

    // Extract file paths (Unix and Windows style)
    const pathMatches = text.match(/(?:\/[\w.-]+(?:\/[\w.-]+)+|[A-Z]:\\[\w.-]+(?:\\[\w.-]+)+)/g)
    if (pathMatches) {
      for (const p of pathMatches) filePaths.add(p)
    }

    // Keep short summaries of user messages as task context
    if (msg.role === 'user') {
      const trimmed = text.slice(0, 150).trim()
      if (trimmed) parts.push(`User: ${trimmed}`)
    }

    // Keep short summaries of assistant conclusions
    if (msg.role === 'assistant') {
      const trimmed = text.slice(0, 200).trim()
      if (trimmed) decisions.push(trimmed)
    }
  }

  const sections: string[] = []

  if (parts.length > 0) {
    sections.push('Tasks discussed:\n' + parts.map((p) => `- ${p}`).join('\n'))
  }

  if (decisions.length > 0) {
    // Keep only last few decisions to stay concise
    const recent = decisions.slice(-5)
    sections.push('Key points:\n' + recent.map((d) => `- ${d}`).join('\n'))
  }

  if (filePaths.size > 0) {
    const paths = Array.from(filePaths).slice(0, 20)
    sections.push('Files referenced:\n' + paths.map((p) => `- ${p}`).join('\n'))
  }

  return sections.join('\n\n') || 'Previous conversation with no extractable context.'
}

/**
 * Compress conversation history when it gets too long.
 * Keeps the last `keepRecent` messages and summarizes the rest
 * into a single user message.
 */
export function compactMessages(
  messages: UnifiedMessage[],
  maxMessages: number = 40,
  keepRecent: number = 10,
): CompactResult {
  const originalCount = messages.length

  // No compaction needed
  if (messages.length <= maxMessages) {
    return {
      compactedMessages: messages,
      summary: '',
      originalCount,
      compactedCount: messages.length,
    }
  }

  // Separate system messages (always keep them)
  const systemMessages = messages.filter((m) => m.role === 'system')
  const nonSystemMessages = messages.filter((m) => m.role !== 'system')

  // Split into older messages (to summarize) and recent messages (to keep)
  const cutoff = nonSystemMessages.length - keepRecent
  const olderMessages = nonSystemMessages.slice(0, cutoff)
  const recentMessages = nonSystemMessages.slice(cutoff)

  // Build summary from older messages
  const summary = buildSummary(olderMessages)

  // Create summary message
  const summaryMessage: UnifiedMessage = {
    role: 'user',
    content: `[Previous conversation summary: ${summary}]`,
  }

  // Reassemble: system messages + summary + recent
  const compactedMessages: UnifiedMessage[] = [
    ...systemMessages,
    summaryMessage,
    ...recentMessages,
  ]

  return {
    compactedMessages,
    summary,
    originalCount,
    compactedCount: compactedMessages.length,
  }
}
