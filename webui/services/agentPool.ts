/**
 * Multi-Agent / Sub-agent Pool.
 *
 * Manages sub-agents spawned by the main agentic loop. Each sub-agent
 * runs its own mini agentic loop (similar to chatSocket.ts) but without
 * a WebSocket — results are collected in memory and returned to the caller.
 */
import type { UnifiedMessage, ContentBlock, UnifiedStreamEvent, UnifiedToolDef } from '../adapters/types.js'
import { routeChat } from '../adapters/router.js'
import { buildSystemPrompt } from '../tools/systemPrompt.js'
import { getAllTools, executeToolCalls } from '../tools/executor.js'
import type { ToolCall } from '../tools/types.js'

// ─── Types ───────────────────────────────────────────────────

export interface SubAgent {
  id: string
  parentSessionId: string
  name: string
  type: 'explore' | 'plan' | 'general' | 'verify'
  status: 'running' | 'completed' | 'error'
  messages: UnifiedMessage[]
  result?: string
  error?: string
  createdAt: number
}

const MAX_SUB_AGENT_ITERATIONS = 15

/**
 * Augment the base system prompt with sub-agent context based on type.
 */
function buildSubAgentSystemPrompt(type: SubAgent['type']): string {
  const base = buildSystemPrompt()

  const typeContext: Record<SubAgent['type'], string> = {
    explore: [
      '## Sub-Agent Role: Explorer',
      'You are an exploration sub-agent. Your job is to gather information using read-only tools.',
      'Do NOT modify any files or run destructive commands.',
      'Focus on reading files, searching code, and summarizing findings.',
    ].join('\n'),
    plan: [
      '## Sub-Agent Role: Planner',
      'You are a planning sub-agent. Your job is to analyze a task and produce a step-by-step plan.',
      'You may read files and search code to inform your plan, but do NOT make changes.',
      'Output a clear, actionable plan as your final response.',
    ].join('\n'),
    general: [
      '## Sub-Agent Role: General',
      'You are a general-purpose sub-agent. You can use all available tools to complete your task.',
      'Work autonomously and return a concise summary of what you did.',
    ].join('\n'),
    verify: [
      '## Sub-Agent Role: Verifier',
      'You are a verification sub-agent. Your job is to verify that something is correct.',
      'Run tests, check file contents, validate outputs. Report pass/fail with details.',
      'Do NOT make changes — only observe and report.',
    ].join('\n'),
  }

  return `${base}\n\n${typeContext[type]}\n\nYou are running as a sub-agent. Be concise and focused on the task. Return your final answer as plain text.`
}

// ─── Agent Pool ──────────────────────────────────────────────

/** Agent pool manages sub-agents spawned by the main agent */
export class AgentPool {
  private agents: Map<string, SubAgent> = new Map()

  /** Spawn a new sub-agent with a task */
  async spawnAgent(opts: {
    parentSessionId: string
    name: string
    type: SubAgent['type']
    task: string
    model: string
    provider: string
  }): Promise<SubAgent> {
    const agent: SubAgent = {
      id: crypto.randomUUID(),
      parentSessionId: opts.parentSessionId,
      name: opts.name,
      type: opts.type,
      status: 'running',
      messages: [
        { role: 'user', content: opts.task },
      ],
      createdAt: Date.now(),
    }

    this.agents.set(agent.id, agent)
    return agent
  }

  /** Get agent status */
  getAgent(agentId: string): SubAgent | undefined {
    return this.agents.get(agentId)
  }

  /** List agents for a session */
  listAgents(sessionId: string): SubAgent[] {
    return Array.from(this.agents.values())
      .filter((a) => a.parentSessionId === sessionId)
      .sort((a, b) => b.createdAt - a.createdAt)
  }

  getAllAgents(): SubAgent[] {
    return Array.from(this.agents.values())
      .sort((a, b) => b.createdAt - a.createdAt)
  }

  removeAgent(agentId: string): boolean {
    return this.agents.delete(agentId)
  }

  /** Run agent's task using the agentic loop */
  async runAgent(agentId: string, signal?: AbortSignal): Promise<string> {
    const agent = this.agents.get(agentId)
    if (!agent) {
      throw new Error(`Agent "${agentId}" not found`)
    }

    const systemPrompt = buildSubAgentSystemPrompt(agent.type)

    // Resolve model/provider from the parent session's config
    // (caller is expected to pass these when spawning)
    const config = await import('../config/modelsConfig.js').then((m) => m.readModelsConfig())
    const model = config.defaultModel
    const provider = config.defaultProvider

    const unifiedTools: UnifiedToolDef[] = getAllTools().map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: t.inputSchema,
    }))

    try {
      let iterations = 0

      while (iterations < MAX_SUB_AGENT_ITERATIONS) {
        if (signal?.aborted) {
          agent.status = 'error'
          agent.error = 'Aborted'
          return 'Agent was aborted.'
        }

        iterations++

        // ── Call the AI ──
        const chatRequest = {
          messages: agent.messages,
          model,
          provider,
          systemPrompt,
          stream: true,
          maxTokens: 8192,
          tools: unifiedTools,
        }

        const assistantBlocks: ContentBlock[] = []
        const toolCalls: ToolCall[] = []
        let currentText = ''
        let stopReason = 'end_turn'
        const pendingToolCalls = new Map<string, { name: string; inputJson: string }>()

        for await (const event of routeChat(chatRequest, signal)) {
          if (signal?.aborted) break

          switch (event.type) {
            case 'stream_text_delta':
              currentText += event.text
              break

            case 'stream_tool_use_start':
              pendingToolCalls.set(event.toolId, { name: event.toolName, inputJson: '' })
              break

            case 'stream_tool_use_delta': {
              const pending = pendingToolCalls.get(event.toolId)
              if (pending) pending.inputJson += event.inputDelta
              break
            }

            case 'stream_tool_use_end': {
              if (currentText) {
                assistantBlocks.push({ type: 'text', text: currentText })
                currentText = ''
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
                currentText = ''
              }
              stopReason = event.stopReason || 'end_turn'
              break

            case 'stream_error':
              throw new Error(event.error)
          }
        }

        // Save assistant message
        if (assistantBlocks.length > 0) {
          agent.messages.push({ role: 'assistant', content: [...assistantBlocks] })
        }

        // No tool calls — we're done
        if (toolCalls.length === 0 || stopReason !== 'tool_use') {
          const finalText = assistantBlocks
            .filter((b): b is { type: 'text'; text: string } => b.type === 'text')
            .map((b) => b.text)
            .join('\n')

          agent.status = 'completed'
          agent.result = finalText
          return finalText
        }

        // Execute tool calls
        const toolResults = await executeToolCalls(toolCalls, {
          cwd: process.cwd(),
          abortSignal: signal,
          // Sub-agents auto-approve everything (no user interaction)
        })

        // Feed results back
        const toolResultBlocks: ContentBlock[] = toolResults.map((r) => ({
          type: 'tool_result' as const,
          tool_use_id: r.tool_call_id,
          content: r.output,
          is_error: r.isError,
        }))

        agent.messages.push({ role: 'user', content: toolResultBlocks })
      }

      // Hit iteration limit
      const partialText = agent.messages
        .filter((m) => m.role === 'assistant')
        .flatMap((m) => (Array.isArray(m.content) ? m.content : []))
        .filter((b): b is { type: 'text'; text: string } => typeof b === 'object' && 'type' in b && b.type === 'text')
        .map((b) => b.text)
        .join('\n')

      agent.status = 'completed'
      agent.result = partialText || 'Sub-agent reached iteration limit without a final response.'
      return agent.result
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err)
      agent.status = 'error'
      agent.error = errMsg
      agent.result = `Error: ${errMsg}`
      return agent.result
    }
  }
}

export const agentPool = new AgentPool()
