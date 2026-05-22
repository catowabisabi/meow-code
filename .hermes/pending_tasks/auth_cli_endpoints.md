# Task: CLI Auth Endpoints — authLogin() / performLogout()

## Context

You are building a TypeScript CLI auth module for Cato Claude. The frontend auth service already exists at `frontend/src/services/auth.ts` with login/register/refresh/getMe/logout.

The new CLI auth module should live in `shared/auth/cli.ts` and provide:
- `authLogin(username, password)` → calls POST /auth/login
- `performLogout()` → calls POST /auth/logout (clears stored token)
- `authStatus()` → calls GET /auth/me, returns current user or null

## Source Files (read before starting)
- `frontend/src/services/auth.ts` — frontend auth service pattern
- `api_server/routes/auth/routes.py` — backend route schemas and endpoints  
- `api_server/routes/auth/schemas.py` — Pydantic models (LoginRequest, TokenResponse, UserResponse)

## Deliverables

1. `shared/auth/cli.ts`:
   - `authLogin(username: string, password: string): Promise<AuthUser>` — login and store tokens
   - `performLogout(): Promise<void>` — clear tokens, call logout endpoint
   - `authStatus(): Promise<AuthUser | null>` — get current user from /auth/me
   - `AuthUser` interface matching `TokenResponse["user"]`
   - Token storage: use a simple JSON file at `~/.cato/auth.json` (token, refreshToken, user)
   - `loadStoredAuth()` helper to restore session on startup

2. `shared/auth/cli.test.ts`:
   - Mock fetch for /auth/login, /auth/logout, /auth/me
   - Test login → stores token, test logout → clears, test authStatus → returns user

3. `shared/auth/index.ts` — re-export cli.ts

## Implementation Notes
- Use native `fetch` (Node 18+), no axios
- Handle 401 → return null for authStatus (not an error)
- Token path: `path.join(os.homedir(), '.cato', 'auth.json')`
- Error on login failure: throw AuthError with message from backend

## Keywords
jwt, cli, session

## Verification
- [ ] authLogin returns AuthUser matching UserResponse shape
- [ ] performLogout clears auth.json
- [ ] authStatus returns null when not logged in
- [ ] All tests pass

ULW