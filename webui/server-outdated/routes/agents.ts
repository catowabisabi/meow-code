/**
 * REST API for agent/subagent management.
 */
import { agentPool } from '../../services/agentPool.js'

export function registerAgentRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  router.set('GET:/api/agents', async (req) => {
    const url = new URL(req.url)
    const sessionId = url.searchParams.get('sessionId')
    if (sessionId) {
      const agents = agentPool.listAgents(sessionId)
      return Response.json({ agents, count: agents.length })
    }
    return Response.json({ agents: agentPool.getAllAgents(), count: agentPool.getAllAgents().length })
  })

  router.set('GET:/api/agents/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.searchParams.get('id')
    if (!id) return Response.json({ error: 'id required' }, { status: 400 })
    const agent = agentPool.getAgent(id)
    if (!agent) return Response.json({ error: 'Agent not found' }, { status: 404 })
    return Response.json({ agent })
  })

  router.set('POST:/api/agents', async (req) => {
    try {
      const body = await req.json() as {
        name: string
        type: 'explore' | 'plan' | 'general' | 'verify'
        task: string
        sessionId?: string
      }
      if (!body.name || !body.task) {
        return Response.json({ error: 'name and task are required' }, { status: 400 })
      }
      const config = await import('../../config/modelsConfig.js').then((m) => m.readModelsConfig())
      const agent = await agentPool.spawnAgent({
        parentSessionId: body.sessionId || 'webui',
        name: body.name,
        type: body.type || 'general',
        task: body.task,
        model: config.defaultModel,
        provider: config.defaultProvider,
      })
      return Response.json({ ok: true, agent })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('POST:/api/agents/:id/run', async (req) => {
    const url = new URL(req.url)
    const id = url.searchParams.get('id')
    if (!id) return Response.json({ error: 'id required' }, { status: 400 })
    try {
      const result = await agentPool.runAgent(id)
      return Response.json({ ok: true, result })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('DELETE:/api/agents/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.searchParams.get('id')
    if (!id) return Response.json({ error: 'id required' }, { status: 400 })
    agentPool.removeAgent(id)
    return Response.json({ ok: true })
  })
}
