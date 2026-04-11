/**
 * Read/write model provider configurations from ~/.claude/models.json
 */
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { type ModelsConfig, type ProviderConfig, DEFAULT_MODELS_CONFIG } from './types.js'

function getConfigPath(): string {
  const claudeDir = path.join(os.homedir(), '.claude')
  if (!fs.existsSync(claudeDir)) {
    fs.mkdirSync(claudeDir, { recursive: true })
  }
  return path.join(claudeDir, 'models.json')
}

export function readModelsConfig(): ModelsConfig {
  const configPath = getConfigPath()
  try {
    if (fs.existsSync(configPath)) {
      const raw = fs.readFileSync(configPath, 'utf-8')
      const parsed = JSON.parse(raw)
      // Merge with defaults to fill any missing fields
      return {
        ...DEFAULT_MODELS_CONFIG,
        ...parsed,
        providers: {
          ...DEFAULT_MODELS_CONFIG.providers,
          ...parsed.providers,
        },
      }
    }
  } catch {
    // Fall through to default
  }
  return { ...DEFAULT_MODELS_CONFIG }
}

export function writeModelsConfig(config: ModelsConfig): void {
  const configPath = getConfigPath()
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8')
}

export function getProvider(providerId: string): ProviderConfig | undefined {
  const config = readModelsConfig()
  return config.providers[providerId]
}

export function setProvider(providerId: string, provider: ProviderConfig): ModelsConfig {
  const config = readModelsConfig()
  config.providers[providerId] = provider
  writeModelsConfig(config)
  return config
}

export function removeProvider(providerId: string): ModelsConfig {
  const config = readModelsConfig()
  delete config.providers[providerId]
  // Reset default if it was pointing to removed provider
  if (config.defaultProvider === providerId) {
    const remaining = Object.keys(config.providers)
    if (remaining.length > 0) {
      config.defaultProvider = remaining[0]!
      const firstProvider = config.providers[remaining[0]!]!
      config.defaultModel = firstProvider.models[0] || ''
    } else {
      config.defaultProvider = ''
      config.defaultModel = ''
    }
  }
  writeModelsConfig(config)
  return config
}

export function setDefaultModel(providerId: string, model: string): ModelsConfig {
  const config = readModelsConfig()
  config.defaultProvider = providerId
  config.defaultModel = model
  writeModelsConfig(config)
  return config
}

export function updateHotkeys(hotkeys: ModelsConfig['hotkeys']): ModelsConfig {
  const config = readModelsConfig()
  config.hotkeys = hotkeys
  writeModelsConfig(config)
  return config
}

/**
 * Get all enabled providers with their models as a flat list.
 */
export function getAvailableModels(): Array<{
  providerId: string
  providerName: string
  model: string
  type: string
}> {
  const config = readModelsConfig()
  const result: Array<{
    providerId: string
    providerName: string
    model: string
    type: string
  }> = []

  for (const [id, provider] of Object.entries(config.providers)) {
    if (provider.enabled && provider.apiKey) {
      for (const model of provider.models) {
        result.push({
          providerId: id,
          providerName: provider.displayName || id,
          model,
          type: provider.type,
        })
      }
    }
  }

  return result
}
