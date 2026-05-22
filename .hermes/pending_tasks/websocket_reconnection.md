# Task: WebSocket Reconnection — Exponential Backoff + Connection State

## Context

Cato Claude's WebSocket client (chat/ws) disconnects on network hiccups and never recovers. Users must manually refresh the page. In production environments this is unacceptable — the client must detect disconnection and reconnect automatically with exponential backoff.

## Source Files (read before starting)
- `api_server/ws/chat.py` — WebSocket endpoint handler
- `webui/client/src/services/websocket.ts` — existing WebSocket client (if any)
- `webui/client/src/hooks/useWebSocket.ts` — existing hook pattern
- `webui/client/src/stores/chatStore.ts` — connection state store

## Deliverables

1. **Backend: WebSocket heartbeat/ping** (`api_server/ws/chat.py`):
   - Add `ping` interval every 30s to keep connection alive
   - Handle `pong` response, log if missed

2. **Backend: Connection close handler**:
   - On unexpected close, emit `disconnect` event with `code` and `reason`

3. **Frontend: WebSocket client with auto-reconnect** (`webui/client/src/services/websocket.ts`):
   - `connect()` — establishes WS connection
   - `disconnect()` — cleanly closes
   - Auto-reconnect logic with exponential backoff:
     - Base delay: 1000ms, multiplier: 2x, max delay: 30000ms, max attempts: 10
     - Jitter: random 0-500ms added to prevent thundering herd
   - `onOpen`, `onClose`, `onError` callbacks
   - Exponential backoff state: `{ attempt, nextRetryMs, state: 'connecting'|'reconnecting'|'failed' }`

4. **Frontend: Connection state indicator** (`webui/client/src/components/ConnectionStatus.tsx`):
   - Badge showing: 🟢 Connected | 🟡 Reconnecting (3s...) | 🔴 Disconnected
   - Show in ChatPage header
   - Auto-dismiss success toast when reconnected

5. **Frontend: Graceful degradation**:
   - When disconnected, queue any outgoing messages, replay on reconnect
   - Show "Connection lost — reconnecting..." banner, dismiss on reconnect
   - Prevent duplicate message sends during reconnect

## Keywords
social proof, attention pulse, constraint

## Verification
- [ ] Network tab shows auto-reconnect attempts with increasing delays
- [ ] ConnectionStatus badge shows correct state transitions
- [ ] Disconnect → reconnect cycle recovers messages
- [ ] Backend ping/pong keeps connection alive for 30s+ idle
- [ ] After 10 failed attempts, show permanent "Connection failed — please refresh" state

ULW