import sys
sys.path.insert(0, 'F:/codebase/cato-claude/api_server')

from db.settings_db import init_issues_db, add_issue, get_all_issues

init_issues_db()
print('Issues DB initialized')

issues = [
    ('WS-001','workspace_pollution','high','currentFolder is global state shared between cowork and code modes','layoutStore.currentFolder is not reset when switching between /cowork and /code modes, causing workspace pollution','webui/client/src/stores/layoutStore.ts',31,'1. Open /cowork set folder 2. Navigate to /code 3. Check folder persists'),
    ('WS-002','workspace_pollution','high','Session folder restored without validation on page load','CoworkPage.tsx restores folder from session data without validating path safety','webui/client/src/pages/CoworkPage.tsx',538,'1. Create session with folder 2. Reload page 3. Folder restored without validation'),
    ('WS-003','workspace_pollution','medium','Folder sent in WebSocket messages but not cleared on mode switch','When sending messages, folder is included in payload but not cleared when switching modes','webui/client/src/pages/CoworkPage.tsx',703,'1. Open /cowork with folder A 2. Send message 3. Navigate to /code'),
    ('R-001','router','high','Path prefix matching bug - /chatty matches /chat route','location.pathname.startsWith chat matches /chatty, causing incorrect route matching','webui/client/src/App.tsx',75,'1. Navigate to /chatty 2. Should show 404 but incorrectly shows chat page'),
    ('R-002','router','medium','ChatPage has key prop but CodeModePage does not, causing state reset inconsistency','ChatPage uses key but CodeModePage has no key, leading to inconsistent React behavior','webui/client/src/App.tsx',124,'1. Visit /code/abc123 2. Return to /cowork/def456 3. Check messages'),
    ('R-003','router','low','Route param sessionId lacks validation','URL sessionId parameter is not validated for format or existence before loading','webui/client/src/pages/CoworkPage.tsx',523,'1. Navigate to /cowork/invalid-session-id 2. Check error handling'),
    ('M-001','memory_pollution','critical','wsManager module-level singleton never cleaned up','WebSocket manager with 3 connections persists across React hot reloads and is never garbage collected','webui/client/src/stores/chatStore.ts',40,'1. DevTools Performance Monitor 2. Switch pages 20 times 3. JS Heap should be stable'),
    ('M-002','memory_pollution','high','alwaysAllowedTools grows unbounded when sessions are deleted','chatStore.alwaysAllowedTools keyed by sessionId but never cleaned when sessions deleted','webui/client/src/stores/chatStore.ts',127,'1. Create 10 sessions always-allow tools 2. Delete all 3. Check alwaysAllowedTools'),
    ('M-003','memory_pollution','high','sessionTitles map grows forever never garbage collected','chatStore.sessionTitles accumulates titles for all sessions including deleted ones','webui/client/src/stores/chatStore.ts',136,'1. Create and delete multiple sessions 2. sessionTitles should not contain deleted'),
    ('M-004','memory_pollution','medium','adapterCache in router.ts is never invalidated on config changes','Model adapter cache persists indefinitely and may serve stale config after provider changes','webui/adapters/router.ts',10,'1. Change API key 2. New requests should use new key but cache may be stale'),
    ('M-005','memory_pollution','medium','disconnectModeWs is no-op WebSocket connections never closed','chatStore.disconnectModeWs does nothing connections persist even when navigating away','webui/client/src/stores/chatStore.ts',401,'1. Connect to /cowork WS 2. Navigate to /chat 3. WS should be closed but is not'),
    ('M-006','memory_pollution','medium','clearMessages clears messages but not modeMessages','chatStore.clearMessages only clears messages array not the per-mode modeMessages','webui/client/src/stores/chatStore.ts',254,'1. Add messages to /cowork mode 2. Call clearMessages 3. modeMessages should be empty but is not'),
    ('P-001','permission','critical','requestPermission is None in ToolContext for sub-agents','execute_tool_calls_real passes requestPermission=None so high-risk tools auto-execute for sub-agents','webui/tools/executor.ts',117,'1. Set up a sub-agent 2. Sub-agent tries to execute shell tool 3. Should request permission but does not'),
    ('P-002','permission','high','Permission dialog auto-allows if isToolAllowed returns true on client','CoworkPage auto-sends permission_response=true if client-side isToolAllowed is true but server may have denied','webui/client/src/pages/CoworkPage.tsx',639,'1. Deny permission for a tool 2. Later request same tool again 3. Server should re-prompt but client may auto-allow'),
    ('P-003','permission','medium','permissionMode state may be out of sync between App.tsx and chatStore','Global warning banner checks always-allow but permissionMode default is ask, potential sync issue','webui/client/src/App.tsx',36,'1. Manually set localStorage.permissionMode=always-allow 2. Reload page 3. Warning banner should appear'),
    ('P-004','permission','medium','Always-allow per-session does not persist across page reloads','alwaysAllowedTools is in-memory only does not persist to localStorage','webui/client/src/stores/chatStore.ts',127,'1. Always-allow a tool in session 2. Reload page 3. Tool should NOT still be always-allowed'),
    ('WS-WS-001','websocket','high','Multiple WebSocket connections when switching modes rapidly','Each mode creates its own WebSocket but they may not be properly reused across page navigations','webui/client/src/stores/chatStore.ts',40,'1. DevTools Network WS 2. Switch between modes quickly 3. Count connections'),
    ('WS-WS-002','websocket','medium','WS URL hardcoded as /ws/chat no fallback','If server WS path changes client will silently fail to connect','webui/client/src/stores/chatStore.ts',46,'1. Change server WS path 2. Client does not work but no error'),
    ('WS-WS-003','websocket','low','WebSocket reconnection may cause duplicate messages','If reconnection happens during streaming messages may be duplicated or lost','webui/client/src/hooks/useWebSocket.ts',110,'1. Start streaming long response 2. Force disconnect/reconnect 3. Check duplicates'),
    ('S-001','session','high','In-memory _active_sessions duplicates persisted sessions','routes/sessions.py has both _active_sessions memory and file-based storage causing potential conflicts','api_server/routes/sessions.py',127,'1. Create session via API 2. Create same session via WebSocket 3. Data may be inconsistent'),
    ('S-002','session','medium','Session ID sanitization may cause collisions','sessionStore.ts uses replace that may cause two different IDs to become same path','webui/services/sessionStore.ts',42,'1. Create session with ID abc-123 2. Create session with ID abc_123 3. Both sanitize to same path'),
    ('S-003','session','medium','WebSocket sessions dict grows unbounded','chat.py has in-memory sessions dict that grows until server restart','api_server/ws/chat.py',193,'1. Create many WebSocket sessions 2. Memory grows until restart'),
    ('S-004','session','low','Session fetch failure shows no error UI','CoworkPage silently fails when session fetch returns 404, sets sessionId but no messages or error','webui/client/src/pages/CoworkPage.tsx',556,'1. Navigate to /cowork/nonexistent-session 2. No error shown'),
    ('API-001','api','high','/health endpoint only returns basic status no real checks','GET /health returns ok without checking DB, WS connections, or external services','api_server/main.py',94,'1. Stop API key validation 2. /health still returns ok 3. Should check critical dependencies'),
    ('API-002','api','medium','permissionsAPI.retry uses GET for long command list','GET request with commands as comma-separated string exceeds URL length limits','webui/client/src/api/endpoints.ts',466,'1. Call permissionsAPI.retry with many commands 2. Request may fail or be truncated'),
    ('API-003','api','low','WS ping/pong heartbeat not validated','pong received but no validation client is still connected - zombie connections possible','api_server/ws/chat.py',405,'1. Client disconnects without closing WS properly 2. Server thinks client still connected'),
    ('TQ-001','code_quality','medium','Strange type cast null as unknown as string in CoworkPage','setModeSession(MODE, null as unknown as string) suggests type safety issue','webui/client/src/pages/CoworkPage.tsx',740,'1. Check TypeScript compilation'),
    ('TQ-002','code_quality','low','JSON parse errors swallowed silently in WebSocket handler','useWebSocket.ts catches JSON parse errors but only logs to console, user sees nothing','webui/client/src/hooks/useWebSocket.ts',97,'1. Receive malformed WS message 2. No user notification'),
    ('TQ-003','code_quality','low','Duplicate code in chat.py and sessions.py for session management','Both files implement session CRUD with different logic - should be unified','api_server/ws/chat.py, api_server/routes/sessions.py',None,'1. Compare session handling between WS and REST 2. Should use same service layer'),
]

for issue in issues:
    add_issue(*issue)

print(f'Added {len(issues)} issues')

all_issues = get_all_issues()
print(f'Total issues in database: {len(all_issues)}')

by_category = {}
for issue in all_issues:
    cat = issue['category']
    by_category[cat] = by_category.get(cat, 0) + 1

print('\nBy category:')
for cat, count in by_category.items():
    print(f'  {cat}: {count}')

by_severity = {}
for issue in all_issues:
    sev = issue['severity']
    by_severity[sev] = by_severity.get(sev, 0) + 1

print('\nBy severity:')
for sev, count in by_severity.items():
    print(f'  {sev}: {count}')
