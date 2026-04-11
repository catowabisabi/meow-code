/**
 * API Configuration & Connection Profiles.
 * 
 * Supports multiple backend connections:
 * - Local (Bun server)
 * - Remote (any HTTP server)
 * - Custom WebSocket endpoints
 */

export interface ConnectionProfile {
  id: string
  name: string
  type: 'local' | 'remote' | 'custom'
  // HTTP endpoint (base URL)
  httpUrl: string
  // WebSocket endpoint
  wsUrl: string
  // Optional authentication
  apiKey?: string
  headers?: Record<string, string>
  // For remote/custom connections
  description?: string
}

export interface APIConfig {
  // Active profile ID
  activeProfile: string
  // All profiles
  profiles: Record<string, ConnectionProfile>
}

// Default local profile (Bun server)
export const DEFAULT_LOCAL_PROFILE: ConnectionProfile = {
  id: 'local',
  name: '本地服務器',
  type: 'local',
  httpUrl: '',  // Empty = use current origin
  wsUrl: '',    // Empty = use current origin
  description: '連接到本地 Bun 服務器',
}

// Built-in profiles
export const BUILT_IN_PROFILES: Record<string, ConnectionProfile> = {
  local: DEFAULT_LOCAL_PROFILE,
}

// Storage key
const CONFIG_KEY = 'webui_api_config'

/**
 * Load API config from localStorage
 */
export function loadAPIConfig(): APIConfig {
  try {
    const stored = localStorage.getItem(CONFIG_KEY)
    if (stored) {
      return JSON.parse(stored) as APIConfig
    }
  } catch {
    // Ignore parse errors
  }
  return {
    activeProfile: 'local',
    profiles: BUILT_IN_PROFILES,
  }
}

/**
 * Save API config to localStorage
 */
export function saveAPIConfig(config: APIConfig): void {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

/**
 * Get the currently active profile
 */
export function getActiveProfile(): ConnectionProfile {
  const config = loadAPIConfig()
  return config.profiles[config.activeProfile] || DEFAULT_LOCAL_PROFILE
}

/**
 * Resolve actual URL (empty = use current origin)
 */
export function resolveUrl(base: string, path: string): string {
  if (!base) {
    // Use current origin
    return `${window.location.origin}${path}`
  }
  // Ensure base doesn't end with /
  const normalizedBase = base.replace(/\/$/, '')
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

/**
 * Resolve WebSocket URL
 */
export function resolveWsUrl(base: string, path: string): string {
  if (!base) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${path}`
  }
  // Convert http/https to ws/wss
  const wsBase = base.replace(/^http/, 'ws').replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${wsBase}${normalizedPath}`
}
