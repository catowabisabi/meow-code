/**
 * WebSocket chat handler — FULL AGENTIC LOOP.
 *
 * The core loop:
 *   1. User sends message
 *   2. AI responds (possibly with tool_calls)
 *   3. If tool_calls → execute each tool → collect results
 *   4. Feed tool results back to AI as new messages
 *   5. AI responds again (possibly with more tool_calls)
 *   6. Repeat until AI gives final text (no tool_calls), or max iterations
 *
 * This is what makes the agent autonomous — it can plan, execute,
 * verify, and self-correct in a continuous loop.
 */
import type { ServerWebSocket } from 'bun'
import type { ClientMessage, ServerMessage } from './protocol.js'
import type { UnifiedMessage, ContentBlock, UnifiedStreamEvent, UnifiedToolDef } from '../../adapters/types.js'
import { routeChat } from '../../adapters/router.js'
import { readModelsConfig } from '../../config/modelsConfig.js'
import { executeToolCalls, getAllTools } from '../../tools/executor.js'
import { buildSystemPrompt } from '../../tools/systemPrompt.js'
import type { ToolCall, ToolCallResult } from '../../tools/types.js'
import { isPlanMode } from '../../tools/planTool.js'
import { shouldCompact, compactMessages } from '../../services/compact.js'
import { saveSession } from '../../services/sessionStore.js'
import { generateTitle } from '../../services/sessionStore.js'
import { generateSmartTitle } from '../../services/titleGenerator.js'

const MAX_AGENT_ITERATIONS = 25 // Safety limit for agentic loop

// ─── Session State ────────────────────────────────────────────

interface ChatSession {
  id: string
  model: string
  provider: string
  mode: string
  folder: string | null
  title: string
  messages: UnifiedMessage[]
  createdAt: number
  abortController: AbortController | null
  /** Pending permission requests */
  pendingPermissions: Map<string, {
    resolve: (allowed: boolean) => void
    toolName: string
    input: Record<string, unknown>
  }>
  /** Total iterations in current agent turn */
  iterationCount: number
}

const sessions = new Map<string, ChatSession>()

export function getSession(sessionId: string): ChatSession | undefined {
  return sessions.get(sessionId)
}

export function getAllSessions(): ChatSession[] {
  return Array.from(sessions.values()).sort((a, b) => b.createdAt - a.createdAt)
}

export function createSession(model?: string, provider?: string, mode?: string, folder?: string): ChatSession {
  const config = readModelsConfig()

  // Auto-detect first enabled provider if no default set
  let defaultProvider = config.defaultProvider
  let defaultModel = config.defaultModel
  if (!defaultProvider || !defaultModel) {
    for (const [id, p] of Object.entries(config.providers)) {
      if (p.enabled && p.models.length > 0) {
        defaultProvider = id
        defaultModel = p.models[0]!
        break
      }
    }
  }

  const session: ChatSession = {
    id: crypto.randomUUID(),
    model: model || defaultModel,
    provider: provider || defaultProvider,
    mode: mode || 'chat',
    folder: folder || null,
    title: '',
    messages: [],
    createdAt: Date.now(),
    abortController: null,
    pendingPermissions: new Map(),
    iterationCount: 0,
  }
  sessions.set(session.id, session)
  return session
}

// ─── WebSocket Handler ────────────────────────────────────────

function send(ws: ServerWebSocket<unknown>, msg: ServerMessage) {
  try {
    ws.send(JSON.stringify(msg))
  } catch {
    // WS may be closed
  }
}

export function handleWSOpen(ws: ServerWebSocket<{ sessionId?: string }>) {
  const sessionId = ws.data?.sessionId
  let session: ChatSession | undefined

  // Only use existing session - do NOT create new one on WS open
  if (sessionId) {
    session = sessions.get(sessionId)
  }

  // If we have an existing session, send session_info
  if (session) {
    ;(ws.data as Record<string, unknown>).sessionId = session.id
    send(ws, {
      type: 'session_info',
      sessionId: session.id,
      model: session.model,
      provider: session.provider,
    })
  } else {
    // No session yet - will be created on first user message
    ;(ws.data as Record<string, unknown>).sessionId = null
    send(ws, {
      type: 'session_info',
      sessionId: null,
      model: '',
      provider: '',
    })
  }
}

export async function handleWSMessage(
  ws: ServerWebSocket<{ sessionId?: string }>,
  raw: string | Buffer
) {
  let msg: ClientMessage
  try {
    msg = JSON.parse(typeof raw === 'string' ? raw : raw.toString()) as ClientMessage
  } catch {
    send(ws, { type: 'error', message: 'Invalid JSON message' })
    return
  }

  const sessionId = (ws.data as Record<string, unknown>).sessionId as string
  let session = sessions.get(sessionId)

  switch (msg.type) {
    case 'ping': {
      send(ws, { type: 'pong' })
      return
    }

    case 'user_message': {
      // If the client sends a sessionId, try to look it up (may differ from ws.data.sessionId)
      if (msg.sessionId && !session) {
        session = sessions.get(msg.sessionId)
        if (session) {
          ;(ws.data as Record<string, unknown>).sessionId = session.id
        }
      }

      if (!session) {
        session = createSession(msg.model, msg.provider, (msg as any).mode, (msg as any).folder)
        ;(ws.data as Record<string, unknown>).sessionId = session.id
        // Notify client of the new session so it can store and reuse it
        send(ws, {
          type: 'session_info',
          sessionId: session.id,
          model: session.model,
          provider: session.provider,
        })
      }

      if (msg.model) session.model = msg.model
      if (msg.provider) session.provider = msg.provider

      const contentBlocks: ContentBlock[] = [{ type: 'text', text: msg.content }]
      if (msg.attachments) {
        for (const att of msg.attachments) {
          if (att.type === 'image') {
            contentBlocks.push({
              type: 'image',
              source: { type: 'base64', media_type: att.mimeType, data: att.data },
            })
          }
        }
      }

      session.messages.push({ role: 'user', content: contentBlocks })
      session.iterationCount = 0

      // Start the agentic loop
      await agenticLoop(ws, session)
      break
    }

    case 'abort': {
      if (session?.abortController) {
        session.abortController.abort()
        session.abortController = null
      }
      break
    }

    case 'switch_model': {
      if (session) {
        session.model = msg.model
        session.provider = msg.provider
        send(ws, { type: 'model_switched', model: msg.model, provider: msg.provider })
      }
      break
    }

    case 'permission_response': {
      if (session) {
        const pending = session.pendingPermissions.get(msg.toolUseId)
        if (pending) {
          pending.resolve(msg.allowed)
          session.pendingPermissions.delete(msg.toolUseId)
        }
      }
      break
    }
  }
}

export function handleWSClose(ws: ServerWebSocket<{ sessionId?: string }>) {
  const sessionId = (ws.data as Record<string, unknown>).sessionId as string
  const session = sessions.get(sessionId)
  if (session?.abortController) {
    session.abortController.abort()
    session.abortController = null
  }
}

// ─── THE AGENTIC LOOP ─────────────────────────────────────────

async function agenticLoop(
  ws: ServerWebSocket<unknown>,
  session: ChatSession
) {
  const abortController = new AbortController()
  session.abortController = abortController

  try {
    // ── Context compression: compact if too many messages ────
    if (shouldCompact(session.messages, 40)) {
      const result = compactMessages(session.messages, 40, 10)
      session.messages = result.compactedMessages
      send(ws, {
        type: 'stream_delta',
        contentType: 'text',
        text: '', // Signal compaction happened
      })
    }

    while (session.iterationCount < MAX_AGENT_ITERATIONS) {
      if (abortController.signal.aborted) break

      session.iterationCount++

      // ── Step 1: Call the AI ────────────────────────
      // ── Step 2: Stream the response, collect tool calls ────
      const { assistantBlocks, toolCalls, stopReason } =
        await streamAndCollect(ws, session, abortController)

      if (abortController.signal.aborted) break

      // Save assistant message to history
      if (assistantBlocks.length > 0) {
        session.messages.push({ role: 'assistant', content: [...assistantBlocks] })
      }

      // ── Step 3: If no tool calls, we're done ────
      if (toolCalls.length === 0 || stopReason !== 'tool_use') {
        send(ws, { type: 'stream_end', stopReason: 'end_turn' })
        break
      }

      // ── Step 4: Execute tool calls ────
      send(ws, {
        type: 'stream_delta',
        contentType: 'text',
        text: '', // Signal tool execution phase
      })

      const toolResults = await executeToolCalls(toolCalls, {
        cwd: process.cwd(),
        abortSignal: abortController.signal,
        requestPermission: async (toolName, input, description) => {
          return new Promise<boolean>((resolve) => {
            const permId = crypto.randomUUID()
            session.pendingPermissions.set(permId, { resolve, toolName, input })

            send(ws, {
              type: 'permission_request',
              toolName,
              toolId: permId,
              input,
              description,
            })

            // Auto-approve after 60 seconds (timeout)
            setTimeout(() => {
              if (session.pendingPermissions.has(permId)) {
                session.pendingPermissions.delete(permId)
                resolve(true) // Auto-approve on timeout
              }
            }, 60000)
          })
        },
      }, (event) => {
        // Forward tool execution events to frontend
        switch (event.type) {
          case 'tool_start':
            send(ws, {
              type: 'tool_use_start',
              toolId: event.toolId,
              toolName: event.toolName,
              input: event.input,
            })
            break
          case 'tool_progress':
            send(ws, {
              type: 'stream_delta',
              contentType: 'text',
              text: '', // Progress handled separately
            })
            break
          case 'tool_end':
            send(ws, {
              type: 'tool_result',
              toolId: event.toolId,
              toolName: event.toolName,
              output: event.result.output.slice(0, 5000), // Truncate for WS
              isError: event.result.isError,
            })
            break
        }
      })

      if (abortController.signal.aborted) break

      // ── Step 5: Feed tool results back to AI ────
      // Build tool result content blocks for the next user message
      const toolResultBlocks: ContentBlock[] = toolResults.map((r) => ({
        type: 'tool_result' as const,
        tool_use_id: r.tool_call_id,
        content: r.output,
        is_error: r.isError,
      }))

      session.messages.push({ role: 'user', content: toolResultBlocks })

      // ── Step 6: Loop continues — AI will see tool results and decide next action ────
    }

    if (session.iterationCount >= MAX_AGENT_ITERATIONS) {
      send(ws, {
        type: 'error',
        message: `Agent loop reached maximum iterations (${MAX_AGENT_ITERATIONS}). Stopping to prevent infinite loops.`,
      })
    }
  } catch (err: unknown) {
    if (!abortController.signal.aborted) {
      const msg = err instanceof Error ? err.message : String(err)
      send(ws, { type: 'error', message: msg })
    }
  } finally {
    session.abortController = null

    // Auto-save session after each turn
    try {
      if (session.messages.length > 0) {
        // Use basic title — set session.title so .then() comparison works
        session.title = session.title || generateTitle(session.messages)
        const currentTitle = session.title

        await saveSession({
          id: session.id,
          title: currentTitle,
          mode: session.mode || 'chat',
          folder: session.folder || null,
          model: session.model,
          provider: session.provider,
          messages: session.messages,
          createdAt: session.createdAt,
          updatedAt: Date.now(),
        })

        // Notify client that session was saved (so sidebar can refresh)
        send(ws, {
          type: 'session_info',
          sessionId: session.id,
          model: session.model,
          provider: session.provider,
        })

        // Ask AI to generate/update title (runs in background, non-blocking)
        generateSmartTitle(currentTitle, session.messages, session.model, session.provider)
          .then(async (newTitle) => {
            if (newTitle && newTitle !== currentTitle) {
              session.title = newTitle

              // Save updated title
              await saveSession({
                id: session.id,
                title: newTitle,
                mode: session.mode || 'chat',
                folder: session.folder || null,
                model: session.model,
                provider: session.provider,
                messages: session.messages,
                createdAt: session.createdAt,
                updatedAt: Date.now(),
              })

              // Notify frontend to update sidebar
              send(ws, {
                type: 'title_updated',
                sessionId: session.id,
                title: newTitle,
              })
            }
          })
          .catch(() => {
            // Non-critical
          })
      }
    } catch {
      // Non-critical — don't fail the response
    }
  }
}

// ─── Stream AI Response & Collect Tool Calls ──────────────────

interface StreamResult {
  assistantBlocks: ContentBlock[]
  toolCalls: ToolCall[]
  stopReason: string
}

async function streamAndCollect(
  ws: ServerWebSocket<unknown>,
  session: ChatSession,
  abortController: AbortController,
): Promise<StreamResult> {
  const assistantBlocks: ContentBlock[] = []
  const toolCalls: ToolCall[] = []
  let currentText = ''
  let currentThinking = ''
  let stopReason = 'end_turn'

  // Track tool call state
  const pendingToolCalls = new Map<string, { name: string; inputJson: string }>()

  const planMode = isPlanMode(session.id)
  const systemPrompt = buildSystemPrompt(undefined, planMode)

  // Build tool definitions in unified format for the adapter
  // In plan mode, only expose read-only tools + plan mode toggles
  const allTools = getAllTools()
  const filteredTools = planMode
    ? allTools.filter((t) => t.isReadOnly || t.name === 'enter_plan_mode' || t.name === 'exit_plan_mode' || t.name === 'todo_write')
    : allTools
  const unifiedTools: UnifiedToolDef[] = filteredTools.map((t) => ({
    name: t.name,
    description: t.description,
    inputSchema: t.inputSchema,
  }))

  // Build the actual request with tools
  const chatRequest = {
    messages: session.messages,
    model: session.model,
    provider: session.provider,
    systemPrompt,
    stream: true,
    maxTokens: 8192,
    tools: unifiedTools,
  }

  const isFirst = session.iterationCount === 1

  if (isFirst) {
    send(ws, {
      type: 'stream_start',
      messageId: crypto.randomUUID(),
      sessionId: session.id,
      model: session.model,
      provider: session.provider,
    })
  }

  for await (const event of routeChat(chatRequest, abortController.signal)) {
    if (abortController.signal.aborted) break

    switch (event.type) {
      case 'stream_start':
        if (!isFirst) {
          // For continuation iterations, signal a new stream segment
          send(ws, {
            type: 'stream_start',
            messageId: event.messageId,
            sessionId: session.id,
            model: session.model,
            provider: session.provider,
          })
        }
        break

      case 'stream_text_delta':
        currentText += event.text
        send(ws, { type: 'stream_delta', contentType: 'text', text: event.text })
        break

      case 'stream_thinking_delta':
        currentThinking += event.text
        send(ws, { type: 'stream_delta', contentType: 'thinking', text: event.text })
        break

      case 'stream_tool_use_start':
        pendingToolCalls.set(event.toolId, { name: event.toolName, inputJson: '' })
        break

      case 'stream_tool_use_delta':
        const pending = pendingToolCalls.get(event.toolId)
        if (pending) {
          pending.inputJson += event.inputDelta
        }
        break

      case 'stream_tool_use_end': {
        // Finalize accumulated text
        if (currentText) {
          assistantBlocks.push({ type: 'text', text: currentText })
          currentText = ''
        }
        if (currentThinking) {
          assistantBlocks.push({ type: 'thinking', text: currentThinking })
          currentThinking = ''
        }

        const toolName = pendingToolCalls.get(event.toolId)?.name || ''

        assistantBlocks.push({
          type: 'tool_use',
          id: event.toolId,
          name: toolName,
          input: event.input,
        })

        toolCalls.push({
          id: event.toolId,
          name: toolName,
          arguments: event.input,
        })

        pendingToolCalls.delete(event.toolId)
        break
      }

      case 'stream_end':
        if (currentText) {
          assistantBlocks.push({ type: 'text', text: currentText })
        }
        if (currentThinking) {
          assistantBlocks.push({ type: 'thinking', text: currentThinking })
        }
        stopReason = event.stopReason || 'end_turn'
        break

      case 'stream_error':
        send(ws, { type: 'error', message: event.error })
        break
    }
  }

  return { assistantBlocks, toolCalls, stopReason }
}
