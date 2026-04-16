/**
 * REST API routes for settings management.
 * Language preference is persisted to ~/.claude/settings.json.
 */
import { homedir } from 'os'
import fs from 'fs'
import path from 'path'
import { readModelsConfig, writeModelsConfig, setProvider } from '../../config/modelsConfig.js'
import type { ProviderConfig } from '../../config/types.js'

interface Settings {
  port: number
  defaultModel: string
  defaultProvider: string
  hotkeys: Array<{ key: string; model: string; provider: string }>
  language: string
  systemPrompt: string
}

// ─── User settings persistence (~/.claude/settings.json) ────

const USER_SETTINGS_PATH = path.join(homedir(), '.claude', 'settings.json')

interface UserSettings {
  language: string
  systemPrompt: string
}

function loadUserSettings(): UserSettings {
  try {
    const raw = fs.readFileSync(USER_SETTINGS_PATH, 'utf-8')
    return JSON.parse(raw) as UserSettings
  } catch {
    return { language: '', systemPrompt: '' }
  }
}

function saveUserSettings(settings: UserSettings): void {
  const dir = path.dirname(USER_SETTINGS_PATH)
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(USER_SETTINGS_PATH, JSON.stringify(settings, null, 2), 'utf-8')
}

// In-memory settings store (extends models.json + user settings)
let settingsCache: Settings | null = null

function getSettings(): Settings {
  if (settingsCache) return settingsCache
  const config = readModelsConfig()
  const userSettings = loadUserSettings()
  settingsCache = {
    port: config.port,
    defaultModel: config.defaultModel,
    defaultProvider: config.defaultProvider,
    hotkeys: config.hotkeys,
    language: userSettings.language || '',
    systemPrompt: userSettings.systemPrompt || '',
  }
  return settingsCache
}

export function registerSettingsRoutes(router: Map<string, (req: Request) => Promise<Response>>) {
  // GET /api/settings — Get current settings
  router.set('GET:/api/settings', async () => {
    return Response.json(getSettings())
  })

  // PUT /api/settings — Update settings
  router.set('PUT:/api/settings', async (req) => {
    try {
      const body = await req.json() as Partial<Settings>
      const settings = getSettings()

      if (body.port !== undefined) {
        settings.port = body.port
        const config = readModelsConfig()
        config.port = body.port
        writeModelsConfig(config)
      }
      if (body.defaultModel !== undefined) {
        settings.defaultModel = body.defaultModel
        const config = readModelsConfig()
        config.defaultModel = body.defaultModel
        writeModelsConfig(config)
      }
      if (body.defaultProvider !== undefined) {
        settings.defaultProvider = body.defaultProvider
        const config = readModelsConfig()
        config.defaultProvider = body.defaultProvider
        writeModelsConfig(config)
      }
      if (body.hotkeys !== undefined) {
        settings.hotkeys = body.hotkeys
        const config = readModelsConfig()
        config.hotkeys = body.hotkeys
        writeModelsConfig(config)
      }
      if (body.language !== undefined) {
        settings.language = body.language
        const userSettings = loadUserSettings()
        userSettings.language = body.language
        saveUserSettings(userSettings)
      }
      if (body.systemPrompt !== undefined) {
        settings.systemPrompt = body.systemPrompt
        const userSettings = loadUserSettings()
        userSettings.systemPrompt = body.systemPrompt
        saveUserSettings(userSettings)
      }

      return Response.json({ ok: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('Failed to save settings:', msg)
      return Response.json({ error: msg }, { status: 500 })
    }
  })

  // GET /api/settings/setup-required — Check if any provider has API key configured
  router.set('GET:/api/settings/setup-required', async () => {
    const config = readModelsConfig()
    const hasApiKey = Object.values(config.providers).some(p => p.apiKey && p.apiKey.trim() !== '')
    return Response.json({ setup_required: !hasApiKey })
  })

  // POST /api/settings/api-credentials — Save API credentials for a provider
  router.set('POST:/api/settings/api-credentials', async (req) => {
    try {
      const body = await req.json() as {
        provider: string
        api_key: string
        base_url?: string
      }

      if (!body.provider || !body.api_key) {
        return Response.json({ message: 'provider and api_key are required' }, { status: 400 })
      }

      const config = readModelsConfig()
      const existingProvider = config.providers[body.provider]

      const providerConfig: ProviderConfig = {
        type: existingProvider?.type || body.provider,
        displayName: existingProvider?.displayName || body.provider,
        baseUrl: body.base_url || existingProvider?.baseUrl || '',
        apiKey: body.api_key,
        models: existingProvider?.models || [],
        enabled: true,
      }

      setProvider(body.provider, providerConfig)

      // Set as default provider if no default is set
      if (!config.defaultProvider) {
        config.defaultProvider = body.provider
        config.defaultModel = providerConfig.models[0] || ''
        writeModelsConfig(config)
      }

      return Response.json({ ok: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('Failed to save API credentials:', msg)
      return Response.json({ message: msg }, { status: 500 })
    }
  })
}
