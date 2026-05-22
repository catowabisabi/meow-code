# Task: API Key Management — Keychain/Config read-write

## Context

Cato Claude needs secure API key management. The CLI auth module (`shared/auth/cli.ts`) provides login/logout, but API keys for different providers (Anthropic, OpenAI, DeepSeek, MiniMax, Ollama) need separate management.

## Source Files (read before starting)
- `shared/auth/cli.ts` — existing auth pattern (token storage, fetch wrapper)
- `api_server/core/config.py` — current config loading (SECRET_KEY, DATABASE_URL, etc.)
- `frontend/src/services/auth.ts` — frontend config store pattern
- `.env.example` or `api_server/.env` — existing env var patterns

## Deliverables

1. `shared/config/store.ts`:
   - `ConfigStore` class managing `~/.cato/config.json`
   - Provider API keys: `setKey(provider, key)`, `getKey(provider)`, `deleteKey(provider)`
   - Model preferences: `setModel(provider, model)`, `getModel(provider)`
   - Base URL overrides: `setBaseUrl(provider, url)`, `getBaseUrl(provider)`
   - `loadConfig()` — restore on startup
   - `saveConfig()` — persist after any change
   - File permissions: `0o600` (owner read/write only)

2. `shared/config/index.ts`:
   - Re-export ConfigStore

3. `shared/config/store.test.ts`:
   - Test set/get/delete keys
   - Test file permission (0o600)
   - Test missing file → empty config

## Implementation Notes
- Path: `path.join(os.homedir(), '.cato', 'config.json')`
- Encrypt at rest using Fernet (or similar AES) if feasible, otherwise warn
- CLI command: `cato config set anthropic.key sk-...`
- Use native Node fs, no external deps beyond what's in project

## Keywords
keychain, config, api-key, secure-storage, provider

## Verification
- [ ] setKey/getKey works for each provider
- [ ] File created with 0o600 permissions
- [ ] Missing config file → empty store (no crash)
- [ ] Tests pass

ULW
