/**
 * Routes chat requests to the correct model adapter based on provider config.
 */
import type { ModelAdapter, UnifiedChatRequest, UnifiedStreamEvent } from './types.js'
import type { ProviderConfig } from '../config/types.js'
import { readModelsConfig } from '../config/modelsConfig.js'
import { AnthropicAdapter } from './anthropic.js'
import { OpenAICompatibleAdapter } from './openai.js'

const adapterCache = new Map<string, ModelAdapter>()

function createAdapter(providerId: string, config: ProviderConfig): ModelAdapter {
  switch (config.type) {
    case 'anthropic':
      return new AnthropicAdapter(config)
    case 'ollama':
      // Ollama often doesn't support tool calling well
      return new OpenAICompatibleAdapter(config, false)
    case 'deepseek':
    case 'minimax':
    case 'openai':
    case 'openai-compatible':
    default:
      return new OpenAICompatibleAdapter(config, true)
  }
}

export function getAdapter(providerId: string): ModelAdapter {
  // Check cache
  const cached = adapterCache.get(providerId)
  if (cached) return cached

  const config = readModelsConfig()
  const providerConfig = config.providers[providerId]

  if (!providerConfig) {
    throw new Error(`Provider "${providerId}" not found in config`)
  }

  if (!providerConfig.enabled) {
    throw new Error(`Provider "${providerId}" is not enabled`)
  }

  if (!providerConfig.apiKey) {
    throw new Error(`Provider "${providerId}" has no API key configured`)
  }

  const adapter = createAdapter(providerId, providerConfig)
  adapterCache.set(providerId, adapter)
  return adapter
}

/**
 * Clear adapter cache (e.g., when config changes).
 */
export function clearAdapterCache(): void {
  adapterCache.clear()
}

/**
 * Route a chat request to the appropriate adapter.
 */
export async function* routeChat(
  req: UnifiedChatRequest,
  signal?: AbortSignal
): AsyncGenerator<UnifiedStreamEvent, void, unknown> {
  const adapter = getAdapter(req.provider)
  yield* adapter.chat(req, signal)
}

/**
 * Find which provider owns a given model.
 */
export function findProviderForModel(model: string): string | null {
  const config = readModelsConfig()
  for (const [id, provider] of Object.entries(config.providers)) {
    if (provider.enabled && provider.models.includes(model)) {
      return id
    }
  }
  return null
}

/**
 * Test provider connectivity by making a simple chat request.
 */
export async function testProvider(providerId: string): Promise<{ ok: boolean; error?: string; latencyMs?: number }> {
  try {
    const adapter = getAdapter(providerId)
    const models = adapter.supportedModels()
    if (models.length === 0) {
      return { ok: false, error: 'No models configured for this provider' }
    }

    const start = Date.now()
    const req: UnifiedChatRequest = {
      messages: [{ role: 'user', content: 'Hi' }],
      model: models[0]!,
      provider: providerId,
      stream: true,
      maxTokens: 10,
    }

    let gotResponse = false
    for await (const event of adapter.chat(req)) {
      if (event.type === 'stream_text_delta' || event.type === 'stream_start') {
        gotResponse = true
      }
      if (event.type === 'stream_error') {
        return { ok: false, error: event.error }
      }
      // Don't wait for the full response
      if (gotResponse) break
    }

    return { ok: true, latencyMs: Date.now() - start }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    return { ok: false, error: msg }
  }
}
