/**
 * AI-powered session title generator.
 *
 * After each conversation turn, sends the current title + recent messages
 * to the AI and asks it to decide if a better title is needed.
 * Returns the new title or null (keep current).
 */
import type { UnifiedMessage } from '../adapters/types.js'
import { routeChat } from '../adapters/router.js'

/**
 * Ask the AI to generate a better title for the conversation.
 * Returns a new title string, or null if the current title is fine.
 * The AI must respond with valid JSON: { "new_topic": "..." }
 * Use "N/A" if no update needed.
 */
export async function generateSmartTitle(
  currentTitle: string,
  messages: UnifiedMessage[],
  model: string,
  provider: string,
): Promise<string | null> {
  try {
    const recentMessages = messages.slice(-6)
    const summary = recentMessages.map((m) => {
      const role = m.role === 'user' ? 'User' : 'Assistant'
      let text = ''
      if (typeof m.content === 'string') {
        text = m.content
      } else if (Array.isArray(m.content)) {
        text = m.content
          .filter((b: any) => b.type === 'text')
          .map((b: any) => b.text)
          .join(' ')
      }
      if (text.length > 200) text = text.slice(0, 200) + '...'
      return `${role}: ${text}`
    }).join('\n')

    const prompt = `You are a conversation topic generator. Based on the conversation below, decide if the topic should be updated.

existing_topic: "${currentTitle}"

Conversation:
${summary}

Respond with ONLY valid JSON — no explanation, no markdown, no text outside the JSON:
{ "new_topic": "your new topic here" }

Rules:
- If existing_topic already describes the conversation well, respond: { "new_topic": "N/A" }
- Use SAME LANGUAGE as the user's messages
- new_topic must be 15 characters or fewer
- Do NOT include any text outside the JSON block`

    const req = {
      messages: [{ role: 'user' as const, content: prompt }],
      model,
      provider,
      stream: false,
      maxTokens: 60,
    }

    let responseText = ''
    for await (const event of routeChat(req)) {
      if (event.type === 'stream_text_delta') {
        responseText += event.text
      }
      if (event.type === 'stream_error') {
        return null
      }
    }

    const result = responseText.trim()

    console.log('[generateSmartTitle] raw response:', result)

    // Extract JSON from response
    const jsonMatch = result.match(/\{[^}]+\}/)
    if (!jsonMatch) {
      console.log('[generateSmartTitle] no JSON found in response')
      return null
    }

    let parsed: { new_topic?: string }
    try {
      parsed = JSON.parse(jsonMatch[0]!)
    } catch (e) {
      console.log('[generateSmartTitle] JSON parse error:', e)
      return null
    }

    const newTopic = parsed.new_topic
    console.log('[generateSmartTitle] parsed new_topic:', newTopic)

    if (!newTopic || newTopic === 'N/A' || newTopic === currentTitle) {
      console.log('[generateSmartTitle] keeping current title')
      return null
    }

    return newTopic.length > 30 ? newTopic.slice(0, 30) : newTopic
  } catch (e) {
    console.log('[generateSmartTitle] error:', e)
    return null
  }
}
