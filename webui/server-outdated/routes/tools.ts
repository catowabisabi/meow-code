/**
 * REST API for tool management.
 */
import { getAllTools } from '../../tools/executor.js'

export function registerToolRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/tools — List all available tools
  router.set('GET:/api/tools', async () => {
    const tools = getAllTools().map((t) => ({
      name: t.name,
      description: t.description,
      isReadOnly: t.isReadOnly,
      riskLevel: t.riskLevel,
      inputSchema: t.inputSchema,
    }))
    return Response.json({ tools, count: tools.length })
  })
}
