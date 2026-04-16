/**
 * REST API for MCP server configuration.
 */
import fs from 'fs'
import path from 'path'
import { homedir } from 'os'

const MCP_CONFIG_PATH = path.join(homedir(), '.claude', 'mcp_servers.json')

interface MCPServer {
  name: string
  command: string
  args?: string[]
  env?: Record<string, string>
  enabled: boolean
}

interface MCPConfig {
  servers: MCPServer[]
}

function loadMCPServers(): MCPServer[] {
  try {
    if (!fs.existsSync(MCP_CONFIG_PATH)) return []
    const raw = fs.readFileSync(MCP_CONFIG_PATH, 'utf-8')
    const config = JSON.parse(raw) as MCPConfig
    return config.servers || []
  } catch {
    return []
  }
}

function saveMCPServers(servers: MCPServer[]): void {
  const dir = path.dirname(MCP_CONFIG_PATH)
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(MCP_CONFIG_PATH, JSON.stringify({ servers }, null, 2), 'utf-8')
}

export function registerMCPRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  router.set('GET:/api/mcp/servers', async () => {
    const servers = loadMCPServers()
    return Response.json({ servers, count: servers.length })
  })

  router.set('POST:/api/mcp/servers', async (req: Request) => {
    try {
      const body = await req.json() as MCPServer
      if (!body.name || !body.command) {
        return Response.json({ error: 'name and command are required' }, { status: 400 })
      }
      const servers = loadMCPServers()
      if (servers.some((s) => s.name === body.name)) {
        return Response.json({ error: 'Server with this name already exists' }, { status: 409 })
      }
      servers.push({ ...body, enabled: body.enabled ?? true })
      saveMCPServers(servers)
      return Response.json({ ok: true, server: body })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('PUT:/api/mcp/servers/:name', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      const servers = loadMCPServers()
      const idx = servers.findIndex((s) => s.name === name)
      if (idx === -1) return Response.json({ error: 'Server not found' }, { status: 404 })
      const updates = await req.json() as Partial<MCPServer>
      servers[idx] = { ...servers[idx]!, ...updates }
      saveMCPServers(servers)
      return Response.json({ ok: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('DELETE:/api/mcp/servers/:name', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      const servers = loadMCPServers()
      const filtered = servers.filter((s) => s.name !== name)
      if (filtered.length === servers.length) {
        return Response.json({ error: 'Server not found' }, { status: 404 })
      }
      saveMCPServers(filtered)
      return Response.json({ ok: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('PATCH:/api/mcp/servers/:name/enable', async (req: Request) => {
    try {
      const url = new URL(req.url)
      const name = url.searchParams.get('name')
      const enabled = url.searchParams.get('enabled')
      if (!name) return Response.json({ error: 'name is required' }, { status: 400 })
      if (enabled === null) return Response.json({ error: 'enabled is required' }, { status: 400 })
      const servers = loadMCPServers()
      const idx = servers.findIndex((s) => s.name === name)
      if (idx === -1) return Response.json({ error: 'Server not found' }, { status: 404 })
      servers[idx]!.enabled = enabled === 'true'
      saveMCPServers(servers)
      return Response.json({ ok: true, enabled: servers[idx]!.enabled })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  router.set('GET:/api/mcp/templates', async () => {
    const templates = [
      {
        name: 'filesystem',
        label: 'Filesystem',
        description: 'Read, write, and manage files on your computer',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-filesystem', '.'],
      },
      {
        name: 'github',
        label: 'GitHub',
        description: 'Interact with GitHub repositories, issues, and pull requests',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-github'],
      },
      {
        name: 'slack',
        label: 'Slack',
        description: 'Send messages and manage channels in Slack',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-slack'],
      },
      {
        name: 'postgres',
        label: 'PostgreSQL',
        description: 'Query and manage PostgreSQL databases',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-postgres'],
      },
      {
        name: 'brave-search',
        label: 'Brave Search',
        description: 'Search the web using Brave Search API',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-brave-search'],
      },
      {
        name: 'google-maps',
        label: 'Google Maps',
        description: 'Get location details, directions, and distance calculations',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-google-maps'],
      },
      {
        name: 'sentry',
        label: 'Sentry',
        description: 'Retrieve and manage issues from Sentry',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-sentry'],
      },
      {
        name: 'aws-kb-retrieval',
        label: 'AWS KB Retrieval',
        description: 'Query AWS Knowledge Base for Bedrock',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-aws-kb-retrieval-server'],
      },
    ]
    return Response.json({ templates })
  })
}
