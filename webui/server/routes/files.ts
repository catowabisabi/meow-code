/**
 * REST API routes for file operations (used by code editor).
 */
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { execSync } from 'child_process'

export function registerFileRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/files/directories — Get common project directories
  router.set('GET:/api/files/directories', async () => {
    const homeDir = os.homedir()
    const cwd = process.cwd()
    
    const getSubdirs = (dir: string, maxDepth = 1): string[] => {
      try {
        const entries = fs.readdirSync(dir, { withFileTypes: true })
        return entries
          .filter(e => e.isDirectory() && !e.name.startsWith('.') && !e.name.startsWith('node_modules'))
          .slice(0, 20)
          .map(e => path.join(dir, e.name))
      } catch {
        return []
      }
    }

    const directories = [
      { path: cwd, label: '專案 (' + path.basename(cwd) + ')' },
      { path: homeDir, label: '主目錄' },
      ...getSubdirs(cwd, 1).map(p => ({ path: p, label: path.basename(p) })),
      ...getSubdirs(homeDir, 1).map(p => ({ path: p, label: path.basename(p) })),
    ]

    return Response.json({ directories })
  })

  // POST /api/browse-folder — Open native Windows folder picker dialog
  router.set('POST:/api/browse-folder', async () => {
    try {
      const ps = `Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description = 'Select a project folder'; if ($d.ShowDialog() -eq 'OK') { $d.SelectedPath } else { '' }`
      const result = execSync(`powershell -Command "${ps}"`, { encoding: 'utf-8', timeout: 60000 }).trim()
      if (!result) {
        return Response.json({ cancelled: true })
      }
      return Response.json({ path: result })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  // GET /api/files?path=... — List files in a directory
  router.set('GET:/api/files', async (req) => {
    const url = new URL(req.url)
    const dirPath = url.searchParams.get('path') || process.cwd()

    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true })
      const files = entries.map((e) => ({
        name: e.name,
        path: path.join(dirPath, e.name),
        isDirectory: e.isDirectory(),
        isFile: e.isFile(),
      }))

      // Sort: directories first, then files
      files.sort((a, b) => {
        if (a.isDirectory && !b.isDirectory) return -1
        if (!a.isDirectory && b.isDirectory) return 1
        return a.name.localeCompare(b.name)
      })

      return Response.json({ path: dirPath, files })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 400 })
    }
  })

  // GET /api/files/read?path=... — Read file contents
  router.set('GET:/api/files/read', async (req) => {
    const url = new URL(req.url)
    const filePath = url.searchParams.get('path')

    if (!filePath) {
      return Response.json({ error: 'Missing path parameter' }, { status: 400 })
    }

    try {
      const stat = fs.statSync(filePath)
      if (stat.size > 5 * 1024 * 1024) {
        return Response.json({ error: 'File too large (max 5MB)' }, { status: 400 })
      }

      const content = fs.readFileSync(filePath, 'utf-8')
      const ext = path.extname(filePath).slice(1)

      return Response.json({
        path: filePath,
        content,
        language: extToLanguage(ext),
        size: stat.size,
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 400 })
    }
  })

  // POST /api/files/write — Write file contents
  router.set('POST:/api/files/write', async (req) => {
    const body = await req.json() as { path: string; content: string }

    if (!body.path || body.content === undefined) {
      return Response.json({ error: 'Missing path or content' }, { status: 400 })
    }

    try {
      // Ensure directory exists
      const dir = path.dirname(body.path)
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true })
      }

      fs.writeFileSync(body.path, body.content, 'utf-8')
      return Response.json({ ok: true, path: body.path })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 400 })
    }
  })
}

function extToLanguage(ext: string): string {
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', rb: 'ruby', go: 'go', rs: 'rust', java: 'java',
    c: 'c', cpp: 'cpp', h: 'c', hpp: 'cpp', cs: 'csharp',
    json: 'json', yaml: 'yaml', yml: 'yaml', toml: 'toml',
    md: 'markdown', html: 'html', css: 'css', scss: 'scss',
    sh: 'shell', bash: 'shell', zsh: 'shell', ps1: 'powershell',
    sql: 'sql', xml: 'xml', svg: 'xml', vue: 'vue',
    dart: 'dart', kt: 'kotlin', swift: 'swift', r: 'r',
    lua: 'lua', php: 'php', pl: 'perl',
  }
  return map[ext] || 'plaintext'
}
