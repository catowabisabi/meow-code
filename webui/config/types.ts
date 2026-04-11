/**
 * Configuration types for multi-model provider management.
 * Stored in ~/.claude/models.json
 */

export interface ProviderConfig {
  /** Provider type: 'anthropic' | 'openai-compatible' | 'deepseek' | 'minimax' | 'openai' | 'ollama' */
  type: string
  /** Display name for the UI */
  displayName?: string
  /** API base URL */
  baseUrl: string
  /** API key (stored locally) */
  apiKey: string
  /** Available model IDs */
  models: string[]
  /** Whether this provider is enabled */
  enabled: boolean
  /** Custom headers to send with requests */
  customHeaders?: Record<string, string>
}

export interface HotkeyBinding {
  /** e.g. "ctrl+1", "ctrl+shift+d" */
  key: string
  /** Model ID to switch to */
  model: string
  /** Provider ID this model belongs to */
  provider: string
}

export interface ModelsConfig {
  /** Provider configurations keyed by provider ID */
  providers: Record<string, ProviderConfig>
  /** Default model to use */
  defaultModel: string
  /** Default provider for the default model */
  defaultProvider: string
  /** Hotkey bindings for quick model switching */
  hotkeys: HotkeyBinding[]
  /** WebUI server port */
  port: number
  /** Notion integration config */
  notion?: { apiKey: string }
}

export const DEFAULT_MODELS_CONFIG: ModelsConfig = {
  providers: {
    deepseek: {
      type: 'deepseek',
      displayName: 'DeepSeek',
      baseUrl: 'https://api.deepseek.com/v1',
      apiKey: '',
      models: ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
      enabled: false,
    },
    minimax: {
      type: 'minimax',
      displayName: 'MiniMax',
      baseUrl: 'https://api.minimax.io/v1',
      apiKey: '',
      models: ['MiniMax-M2.7', 'MiniMax-M2.5', 'MiniMax-M2.1'],
      enabled: false,
    },
    openai: {
      type: 'openai',
      displayName: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o1-mini', 'o3-mini'],
      enabled: false,
    },
    ollama: {
      type: 'ollama',
      displayName: 'Ollama (Local)',
      baseUrl: 'http://localhost:11434/v1',
      apiKey: 'ollama',
      models: ['llama3', 'codellama', 'mistral', 'qwen2.5-coder'],
      enabled: false,
    },
  },
  defaultModel: '',
  defaultProvider: '',
  hotkeys: [
    { key: 'ctrl+1', model: 'deepseek-chat', provider: 'deepseek' },
    { key: 'ctrl+2', model: 'gpt-4o', provider: 'openai' },
    { key: 'ctrl+3', model: 'MiniMax-Text-01', provider: 'minimax' },
  ],
  port: 3456,
}
