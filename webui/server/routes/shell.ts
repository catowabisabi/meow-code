/**
 * REST API for direct shell execution.
 * Provides a terminal-like interface from the WebUI.
 */
import { executeShellCommand } from '../../tools/shellTool.js'

export function registerShellRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // POST /api/shell — Execute a shell command
  router.set('POST:/api/shell', async (req) => {
    const body = await req.json() as {
      command: string
      cwd?: string
      shell?: 'bash' | 'powershell' | 'cmd' | 'auto'
      timeout?: number
    }

    if (!body.command) {
      return Response.json({ error: 'Missing command' }, { status: 400 })
    }

    const result = await executeShellCommand(
      {
        command: body.command,
        cwd: body.cwd,
        shell: body.shell,
        timeout: body.timeout || 120000,
      },
      {
        cwd: body.cwd || process.cwd(),
      }
    )

    return Response.json({
      output: result.output,
      isError: result.isError,
      metadata: result.metadata,
    })
  })

  // GET /api/shell/cwd — Get current working directory
  router.set('GET:/api/shell/cwd', async () => {
    return Response.json({ cwd: process.cwd() })
  })
}
