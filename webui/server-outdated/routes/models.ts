/**
 * REST API routes for model provider management.
 */
import {
  readModelsConfig,
  writeModelsConfig,
  setProvider,
  removeProvider,
  setDefaultModel,
  updateHotkeys,
  getAvailableModels,
} from '../../config/modelsConfig.js'
import { testProvider } from '../../adapters/router.js'
import { clearAdapterCache } from '../../adapters/router.js'
import { KNOWN_PROVIDERS } from '../../adapters/types.js'

export function registerModelRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/models — List all providers and available models
  router.set('GET:/api/models', async () => {
    const config = readModelsConfig()
    const available = getAvailableModels()
    return Response.json({
      providers: config.providers,
      availableModels: available,
      defaultModel: config.defaultModel,
      defaultProvider: config.defaultProvider,
      hotkeys: config.hotkeys,
      knownProviders: KNOWN_PROVIDERS,
    })
  })

  // POST /api/models — Add a new provider
  router.set('POST:/api/models', async (req) => {
    const body = await req.json() as {
      id: string
      type: string
      displayName?: string
      baseUrl: string
      apiKey: string
      models: string[]
    }

    if (!body.id || !body.type || !body.baseUrl) {
      return Response.json({ error: 'Missing required fields: id, type, baseUrl' }, { status: 400 })
    }

    const config = setProvider(body.id, {
      type: body.type,
      displayName: body.displayName || body.id,
      baseUrl: body.baseUrl,
      apiKey: body.apiKey || '',
      models: body.models || [],
      enabled: true,
    })

    clearAdapterCache()
    return Response.json({ ok: true, providers: config.providers })
  })

  // PUT /api/models/:id — Update a provider
  router.set('PUT:/api/models/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!
    const body = await req.json() as Record<string, unknown>

    const config = readModelsConfig()
    const existing = config.providers[id]
    if (!existing) {
      return Response.json({ error: `Provider "${id}" not found` }, { status: 404 })
    }

    const updated = { ...existing, ...body }
    const newConfig = setProvider(id, updated as typeof existing)
    clearAdapterCache()
    return Response.json({ ok: true, provider: newConfig.providers[id] })
  })

  // DELETE /api/models/:id — Remove a provider
  router.set('DELETE:/api/models/:id', async (req) => {
    const url = new URL(req.url)
    const id = url.pathname.split('/').pop()!
    const config = removeProvider(id)
    clearAdapterCache()
    return Response.json({ ok: true, providers: config.providers })
  })

  // POST /api/models/:id/test — Test provider connectivity
  router.set('POST:/api/models/:id/test', async (req) => {
    const url = new URL(req.url)
    const segments = url.pathname.split('/')
    const id = segments[segments.length - 2]!
    const result = await testProvider(id)
    return Response.json(result)
  })

  // PUT /api/models/default — Set default model
  router.set('PUT:/api/models/default', async (req) => {
    const body = await req.json() as { model: string; provider: string }
    const config = setDefaultModel(body.provider, body.model)
    return Response.json({ ok: true, defaultModel: config.defaultModel, defaultProvider: config.defaultProvider })
  })

  // PUT /api/models/hotkeys — Update hotkey bindings
  router.set('PUT:/api/models/hotkeys', async (req) => {
    const body = await req.json() as { hotkeys: Array<{ key: string; model: string; provider: string }> }
    const config = updateHotkeys(body.hotkeys)
    return Response.json({ ok: true, hotkeys: config.hotkeys })
  })
}
