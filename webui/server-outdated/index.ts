/**
 * WebUI HTTP + WebSocket server.
 * Serves the React frontend and provides REST/WS APIs.
 */
import * as path from 'path'
import * as fs from 'fs'
import { fileURLToPath } from 'url'

// ESM-safe __dirname
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
import { readModelsConfig } from '../config/modelsConfig.js'
import { registerModelRoutes } from './routes/models.js'
import { registerSessionRoutes } from './routes/sessions.js'
import { registerSettingsRoutes } from './routes/settings.js'
import { registerFileRoutes } from './routes/files.js'
import { registerShellRoutes } from './routes/shell.js'
import { registerToolRoutes } from './routes/tools.js'
import { registerSkillRoutes } from './routes/skills.js'
import { registerMemoryRoutes } from './routes/memory.js'
import { registerNotionRoutes } from './routes/notion.js'
import { registerDatabaseRoutes } from './routes/database.js'
import { registerMCPRoutes } from './routes/mcp.js'
import { registerAgentRoutes } from './routes/agents.js'
import { registerBuiltinSkills } from '../skills/builtinSkills.js'
import { handleWSOpen, handleWSMessage, handleWSClose } from './ws/chatSocket.js'

// ─── Route Registry ───────────────────────────────────────────

const routes = new Map<string, (req: Request) => Promise<Response>>()

// Register all API routes
registerModelRoutes(routes)
registerSessionRoutes(routes)
registerSettingsRoutes(routes)
registerFileRoutes(routes)
registerShellRoutes(routes)
registerToolRoutes(routes)
registerSkillRoutes(routes)
registerMemoryRoutes(routes)
registerNotionRoutes(routes)
registerDatabaseRoutes(routes)
registerMCPRoutes(routes)
registerAgentRoutes(routes)

// Register built-in skills at startup
registerBuiltinSkills()

// Health check endpoint for connection testing
routes.set('GET:/api/health', async () => {
  return Response.json({ status: 'ok', timestamp: Date.now() })
})

// ─── Route Matching ───────────────────────────────────────────

function matchRoute(method: string, pathname: string): ((req: Request) => Promise<Response>) | null {
  // Try exact match first
  const exact = routes.get(`${method}:${pathname}`)
  if (exact) return exact

  // Try pattern matching (e.g., /api/models/:id)
  for (const [pattern, handler] of routes) {
    const [routeMethod, routePath] = pattern.split(':/', 2) as [string, string]
    if (routeMethod !== method) continue

    const routeParts = ('/' + routePath).split('/')
    const pathParts = pathname.split('/')

    if (routeParts.length !== pathParts.length) continue

    let match = true
    for (let i = 0; i < routeParts.length; i++) {
      if (routeParts[i]!.startsWith(':')) continue
      if (routeParts[i] !== pathParts[i]) {
        match = false
        break
      }
    }

    if (match) return handler
  }

  return null
}

// ─── CORS Headers ─────────────────────────────────────────────

function corsHeaders(): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  }
}

// ─── Static File Serving ──────────────────────────────────────

const MIME_TYPES: Record<string, string> = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
}

function getClientDistPath(): string {
  // __dirname = src/webui/server  → go up two levels to src/webui, then into client/dist
  return path.resolve(__dirname, '..', 'client', 'dist')
}

/** Serve a friendly setup page when the frontend hasn't been built yet */
function setupPage(distPath: string): Response {
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Code Assistant — 安裝說明</title>
  <style>
    body { font-family: -apple-system, sans-serif; background: #0d1117; color: #e6edf3;
           display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .box { max-width: 600px; padding: 40px; background: #161b22;
           border: 1px solid #30363d; border-radius: 12px; }
    h1 { font-size: 22px; margin-bottom: 12px; }
    p  { color: #8b949e; line-height: 1.6; margin-bottom: 16px; }
    pre { background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
          padding: 16px; font-size: 13px; line-height: 1.8; overflow-x: auto; }
    code { color: #58a6ff; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
             background: #d29922; color: #000; font-size: 12px; font-weight: 700; }
  </style>
</head>
<body>
  <div class="box">
    <h1>⚡ AI Code Assistant WebUI</h1>
    <p><span class="badge">需要構建前端</span></p>
    <p>後端服務已啟動，但前端尚未構建。請在新終端窗口中執行以下命令：</p>
    <pre><code>cd ${distPath.replace(/[/\\]dist$/, '')}
npm install
npm run build</code></pre>
    <p>構建完成後刷新此頁面即可。</p>
    <p style="font-size: 13px; color: #6e7681;">
      🔧 或者使用 Vite 開發服務器（熱重載）：<br>
      <code style="color: #3fb950">npm run dev</code>  → 訪問 <code style="color: #3fb950">http://localhost:7777</code>
    </p>
  </div>
</body>
</html>`
  return new Response(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', ...corsHeaders() },
  })
}

function serveStaticFile(pathname: string): Response | null {
  const distPath = getClientDistPath()
  let filePath = path.join(distPath, pathname)

  // SPA fallback: serve index.html for non-file routes
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(distPath, 'index.html')
  }

  if (!fs.existsSync(filePath)) {
    return null
  }

  const ext = path.extname(filePath)
  const mimeType = MIME_TYPES[ext] || 'application/octet-stream'
  const content = fs.readFileSync(filePath)

  return new Response(content, {
    headers: { 'Content-Type': mimeType, ...corsHeaders() },
  })
}

// ─── Server Bootstrap ─────────────────────────────────────────

export function startWebUI(portOverride?: number) {
  const config = readModelsConfig()
  const port = portOverride || config.port || 7778

  const server = Bun.serve({
    port,
    async fetch(req, server) {
      const url = new URL(req.url)
      const pathname = url.pathname

      // CORS preflight
      if (req.method === 'OPTIONS') {
        return new Response(null, { status: 204, headers: corsHeaders() })
      }

      // WebSocket upgrade for /ws/chat
      if (pathname.startsWith('/ws/chat')) {
        const sessionId = url.searchParams.get('sessionId') || undefined
        const upgraded = server.upgrade(req, { data: { sessionId } })
        if (upgraded) return undefined as unknown as Response
        return new Response('WebSocket upgrade failed', { status: 400 })
      }

      // API routes
      if (pathname.startsWith('/api/')) {
        const handler = matchRoute(req.method, pathname)
        if (handler) {
          try {
            const response = await handler(req)
            // Add CORS headers to response
            const headers = new Headers(response.headers)
            for (const [k, v] of Object.entries(corsHeaders())) {
              headers.set(k, v)
            }
            return new Response(response.body, {
              status: response.status,
              headers,
            })
          } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : String(err)
            return Response.json({ error: msg }, { status: 500, headers: corsHeaders() })
          }
        }
        return Response.json({ error: 'Not found' }, { status: 404, headers: corsHeaders() })
      }

      // Static files / SPA
      const staticResponse = serveStaticFile(pathname)
      if (staticResponse) return staticResponse

      // Fallback: serve index.html (SPA routing)
      const indexResponse = serveStaticFile('/index.html')
      if (indexResponse) return indexResponse

      // Frontend not built yet — show setup instructions
      return setupPage(getClientDistPath())
    },

    websocket: {
      open(ws) {
        handleWSOpen(ws as any)
      },
      message(ws, message) {
        handleWSMessage(ws as any, message as string)
      },
      close(ws) {
        handleWSClose(ws as any)
      },
    },
  })

  console.log(`
╔══════════════════════════════════════════════╗
║         🚀 AI Code Assistant WebUI          ║
║──────────────────────────────────────────────║
║  Local:   http://localhost:${port}              ║
║  WebSocket: ws://localhost:${port}/ws/chat      ║
║──────────────────────────────────────────────║
║  Press Ctrl+C to stop                        ║
╚══════════════════════════════════════════════╝
`)

  return server
}
