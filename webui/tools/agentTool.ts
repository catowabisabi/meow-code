/**
 * Agent tools — allow the AI to spawn and manage sub-agents.
 *
 * agentSpawnTool  — Spawn a sub-agent to perform a task
 * agentStatusTool — Check the status of a sub-agent
 */
import type { ToolDef, ToolContext, ToolResult } from './types.js'
import { agentPool } from '../services/agentPool.js'
import { readModelsConfig } from '../config/modelsConfig.js'

// ─── Agent Spawn Tool ────────────────────────────────────────

interface AgentSpawnInput {
  name: string
  type: 'explore' | 'plan' | 'general' | 'verify'
  task: string
  background?: boolean
}

export const agentSpawnTool: ToolDef = {
  name: 'agent_spawn',
  description: [
    'Spawn a sub-agent to perform a task independently.',
    'Types:',
    '  - explore: Read-only investigation (search code, read files, gather info)',
    '  - plan: Analyze a problem and produce a step-by-step plan',
    '  - general: Full-capability agent that can read/write/execute',
    '  - verify: Run tests or checks to verify correctness (read-only)',
    '',
    'Set background=true to spawn the agent and return immediately with its ID.',
    'Set background=false (default) to wait for the agent to finish and return its result.',
  ].join('\n'),
  inputSchema: {
    type: 'object',
    properties: {
      name: {
        type: 'string',
        description: 'A short descriptive name for the sub-agent (e.g. "find-auth-routes")',
      },
      type: {
        type: 'string',
        enum: ['explore', 'plan', 'general', 'verify'],
        description: 'The type of sub-agent to spawn',
      },
      task: {
        type: 'string',
        description: 'The task description / prompt for the sub-agent',
      },
      background: {
        type: 'boolean',
        description: 'If true, spawn and return immediately with agent ID. Default: false',
      },
    },
    required: ['name', 'type', 'task'],
  },
  isReadOnly: false,
  riskLevel: 'medium',

  async execute(input: Record<string, unknown>, ctx: ToolContext): Promise<ToolResult> {
    const { name, type, task, background } = input as unknown as AgentSpawnInput

    if (!name || !type || !task) {
      return { output: 'Missing required fields: name, type, task', isError: true }
    }

    const validTypes = ['explore', 'plan', 'general', 'verify']
    if (!validTypes.includes(type)) {
      return { output: `Invalid agent type: ${type}. Must be one of: ${validTypes.join(', ')}`, isError: true }
    }

    const config = readModelsConfig()

    const agent = await agentPool.spawnAgent({
      parentSessionId: 'tool-spawned',
      name,
      type,
      task,
      model: config.defaultModel,
      provider: config.defaultProvider,
    })

    if (background) {
      // Fire and forget — run in background
      agentPool.runAgent(agent.id, ctx.abortSignal).catch(() => {
        // Error is captured in agent.error
      })

      return {
        output: JSON.stringify({
          agentId: agent.id,
          name: agent.name,
          type: agent.type,
          status: 'running',
          message: 'Agent spawned in background. Use agent_status to check progress.',
        }, null, 2),
        isError: false,
        metadata: { agentId: agent.id },
      }
    }

    // Synchronous — wait for result
    const result = await agentPool.runAgent(agent.id, ctx.abortSignal)

    return {
      output: JSON.stringify({
        agentId: agent.id,
        name: agent.name,
        type: agent.type,
        status: agent.status,
        result,
      }, null, 2),
      isError: agent.status === 'error',
      metadata: { agentId: agent.id },
    }
  },
}

// ─── Agent Status Tool ───────────────────────────────────────

interface AgentStatusInput {
  agentId: string
}

export const agentStatusTool: ToolDef = {
  name: 'agent_status',
  description: [
    'Check the status of a previously spawned sub-agent.',
    'Returns the agent\'s current status, and its result if completed.',
  ].join('\n'),
  inputSchema: {
    type: 'object',
    properties: {
      agentId: {
        type: 'string',
        description: 'The ID of the sub-agent to check',
      },
    },
    required: ['agentId'],
  },
  isReadOnly: true,
  riskLevel: 'low',

  async execute(input: Record<string, unknown>): Promise<ToolResult> {
    const { agentId } = input as unknown as AgentStatusInput

    if (!agentId) {
      return { output: 'Missing required field: agentId', isError: true }
    }

    const agent = agentPool.getAgent(agentId)
    if (!agent) {
      return { output: `Agent "${agentId}" not found`, isError: true }
    }

    return {
      output: JSON.stringify({
        agentId: agent.id,
        name: agent.name,
        type: agent.type,
        status: agent.status,
        result: agent.result,
        error: agent.error,
        createdAt: agent.createdAt,
        messageCount: agent.messages.length,
      }, null, 2),
      isError: false,
    }
  },
}
