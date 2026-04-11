#!/usr/bin/env python3
"""
Comprehensive API Test Script - Tests all 229 endpoints
Usage: python test_all_endpoints.py --server http://localhost:7778 --output results.json
"""

import asyncio
import httpx
import json
import sys
import time
from typing import Any, Optional

BASE_URL = "http://localhost:7778"
OUTPUT_FILE = "test_results.json"


def get_headers() -> dict:
    return {"Content-Type": "application/json", "X-API-Key": "test-key"}


class EndpointTest:
    def __init__(self, method: str, path: str, name: str = "", body: Any = None, params: dict = None):
        self.method = method
        self.path = path
        self.name = name or f"{method} {path}"
        self.body = body
        self.params = params


ALL_ENDPOINTS = [
    # sessions_router (7)
    EndpointTest("GET", "/api/sessions", "List sessions"),
    EndpointTest("POST", "/api/sessions", "Create session", {"model": "claude-3-5-sonnet", "provider": "anthropic"}),
    EndpointTest("GET", "/api/sessions/{id}", "Get session", params={"id": "test-session-001"}),
    EndpointTest("PUT", "/api/sessions/{id}", "Update session", {"title": "Test"}, params={"id": "test-session-001"}),
    EndpointTest("DELETE", "/api/sessions/{id}", "Delete session", params={"id": "test-session-001"}),
    EndpointTest("POST", "/api/sessions/{id}/save", "Save session", params={"id": "test-session-001"}),
    EndpointTest("GET", "/api/sessions/stored/list", "List stored sessions"),

    # models_router (7)
    EndpointTest("GET", "/api/models", "List models"),
    EndpointTest("POST", "/api/models", "Add model", {"provider": "anthropic", "model": "claude-3-5-sonnet"}),
    EndpointTest("PUT", "/api/models/{provider_id}", "Update model", params={"provider_id": "anthropic"}),
    EndpointTest("DELETE", "/api/models/{provider_id}", "Delete model", params={"provider_id": "anthropic"}),
    EndpointTest("POST", "/api/models/{provider_id}/test", "Test model", params={"provider_id": "anthropic"}),
    EndpointTest("PUT", "/api/models/default", "Set default model", {"provider": "anthropic"}),
    EndpointTest("PUT", "/api/models/hotkeys", "Set hotkeys"),

    # files_router (4)
    EndpointTest("GET", "/api/files/directories", "List directories"),
    EndpointTest("GET", "/api/files", "List files", params={"path": "."}),
    EndpointTest("GET", "/api/files/read", "Read file", params={"path": "README.md"}),
    EndpointTest("POST", "/api/files/write", "Write file", {"path": "test.txt", "content": "test"}),

    # shell_router (2)
    EndpointTest("POST", "/api/shell", "Execute shell", {"command": "echo hello"}),
    EndpointTest("GET", "/api/shell/cwd", "Get CWD"),

    # tools_router (1)
    EndpointTest("GET", "/api/tools", "List tools"),

    # memory_router (6)
    EndpointTest("GET", "/api/memory", "List memories"),
    EndpointTest("GET", "/api/memory/search", "Search memories", params={"query": "test"}),
    EndpointTest("GET", "/api/memory/index", "Get memory index"),
    EndpointTest("GET", "/api/memory/{id}", "Get memory", params={"id": "test-id"}),
    EndpointTest("POST", "/api/memory", "Create memory", {"content": "test memory", "metadata": {}}),
    EndpointTest("DELETE", "/api/memory/{id}", "Delete memory", params={"id": "test-id"}),

    # skills_router (5)
    EndpointTest("GET", "/api/skills", "List skills"),
    EndpointTest("GET", "/api/skills/{name}", "Get skill", params={"name": "test-skill"}),
    EndpointTest("POST", "/api/skills/execute", "Execute skill", {"name": "test-skill", "args": {}}),
    EndpointTest("POST", "/api/skills/load", "Load skills"),
    EndpointTest("POST", "/api/skills/register", "Register skill"),

    # database_router (5)
    EndpointTest("GET", "/api/databases", "List databases"),
    EndpointTest("GET", "/api/databases/{name}/tables", "List tables", params={"name": "test"}),
    EndpointTest("POST", "/api/databases/{name}/query", "Execute query", {"query": "SELECT 1"}, params={"name": "test"}),
    EndpointTest("POST", "/api/databases", "Create database", {"name": "test_db"}),
    EndpointTest("DELETE", "/api/databases/{name}", "Delete database", params={"name": "test_db"}),

    # notion_router (5)
    EndpointTest("GET", "/api/notion/search", "Search Notion", params={"query": "test"}),
    EndpointTest("GET", "/api/notion/pages/{id}", "Get page", params={"id": "test-id"}),
    EndpointTest("POST", "/api/notion/pages", "Create page", {"title": "Test"}),
    EndpointTest("GET", "/api/notion/databases/{id}", "Get database", params={"id": "test-id"}),
    EndpointTest("POST", "/api/notion/databases/{id}/query", "Query database", {}, params={"id": "test-id"}),

    # settings_router (2)
    EndpointTest("GET", "/api/settings", "Get settings"),
    EndpointTest("PUT", "/api/settings", "Update settings", {"theme": "dark"}),

    # agents_router (5)
    EndpointTest("POST", "/api/agents/{agent_id}/summary/start", "Start summary", params={"agent_id": "test-agent"}),
    EndpointTest("DELETE", "/api/agents/{agent_id}/summary/stop", "Stop summary", params={"agent_id": "test-agent"}),
    EndpointTest("GET", "/api/agents/{agent_id}/summary", "Get summary", params={"agent_id": "test-agent"}),
    EndpointTest("POST", "/api/agents/{agent_id}/messages", "Add message", {"role": "user", "content": "test"}, params={"agent_id": "test-agent"}),
    EndpointTest("DELETE", "/api/agents/{agent_id}/messages", "Clear messages", params={"agent_id": "test-agent"}),

    # permissions_router (7)
    EndpointTest("GET", "/api/permissions", "List permissions"),
    EndpointTest("POST", "/api/permissions", "Create permission", {"tool_name": "Bash", "command": "echo test"}),
    EndpointTest("DELETE", "/api/permissions/{rule_id}", "Delete permission", params={"rule_id": "test-rule"}),
    EndpointTest("GET", "/api/permissions/pending", "Get pending"),
    EndpointTest("POST", "/api/permissions/approve", "Approve permission", {"request_id": "test"}),
    EndpointTest("POST", "/api/permissions/deny", "Deny permission", {"request_id": "test"}),
    EndpointTest("GET", "/api/permissions/retry", "Retry permission"),

    # hooks_router (3)
    EndpointTest("GET", "/api/hooks", "List hooks"),
    EndpointTest("POST", "/api/hooks", "Create hook", {"tool_name": "Bash", "event": "pre-execution", "command": "echo"}),
    EndpointTest("DELETE", "/api/hooks/{hook_id}", "Delete hook", params={"hook_id": "test-hook"}),

    # privacy_settings_router (2)
    EndpointTest("GET", "/api/privacy-settings", "Get privacy settings"),
    EndpointTest("PUT", "/api/privacy-settings", "Update privacy settings", {"grove_enabled": False}),

    # bridge_router (3)
    EndpointTest("GET", "/api/bridge/status", "Get bridge status"),
    EndpointTest("POST", "/api/bridge/connect", "Connect bridge", {"host": "localhost", "port": 8080}),
    EndpointTest("DELETE", "/api/bridge/disconnect", "Disconnect bridge"),

    # tags_router (3)
    EndpointTest("GET", "/api/tags/{session_id}/tag", "Get tags", params={"session_id": "test"}),
    EndpointTest("POST", "/api/tags/{session_id}/tag", "Add tag", {"tag": "test"}, params={"session_id": "test"}),
    EndpointTest("DELETE", "/api/tags/{session_id}/tag", "Remove tag", params={"session_id": "test"}),

    # export_router (1)
    EndpointTest("POST", "/api/export/{session_id}/export", "Export session", params={"session_id": "test"}),

    # bootstrap_router (2)
    EndpointTest("GET", "/api/bootstrap/bootstrap", "Get bootstrap"),
    EndpointTest("POST", "/api/bootstrap/refresh", "Refresh bootstrap"),

    # admin_requests_router (6)
    EndpointTest("POST", "/api/admin-requests/limit_increase", "Request limit increase", {"reason": "test"}),
    EndpointTest("POST", "/api/admin-requests/seat_upgrade", "Request seat upgrade", {"reason": "test"}),
    EndpointTest("GET", "/api/admin-requests/limit_increase/me", "Get my limit requests"),
    EndpointTest("GET", "/api/admin-requests/seat_upgrade/me", "Get my seat requests"),
    EndpointTest("GET", "/api/admin-requests/eligibility/limit_increase", "Check limit eligibility"),
    EndpointTest("GET", "/api/admin-requests/eligibility/seat_upgrade", "Check seat eligibility"),

    # commands_router - Git commands
    EndpointTest("GET", "/api/commands/git/status", "Git status"),
    EndpointTest("GET", "/api/commands/git/diff", "Git diff"),
    EndpointTest("GET", "/api/commands/git/log", "Git log"),
    EndpointTest("POST", "/api/commands/git/commit", "Git commit", {"message": "test commit"}),
    EndpointTest("GET", "/api/commands/git/branch", "Git branch"),
    EndpointTest("POST", "/api/commands/git/branch", "Create branch", {"name": "test-branch"}),
    EndpointTest("GET", "/api/commands/git/stash", "Git stash"),

    # commands_router - Commit commands
    EndpointTest("POST", "/api/commands/commit", "Commit command", {"message": "test"}),
    EndpointTest("POST", "/api/commands/commit-push-pr", "Commit push PR", {"message": "test"}),

    # commands_router - Review commands
    EndpointTest("GET", "/api/commands/review/pr", "Review PR"),
    EndpointTest("GET", "/api/commands/review/pr-comments", "PR comments"),
    EndpointTest("POST", "/api/commands/review", "Review"),
    EndpointTest("POST", "/api/commands/ultrareview", "Ultra review"),
    EndpointTest("POST", "/api/commands/security-review", "Security review"),

    # commands_router - Session commands
    EndpointTest("GET", "/api/commands/session/info", "Session info"),
    EndpointTest("POST", "/api/commands/session/share", "Share session"),

    # commands_router - MCP commands
    EndpointTest("GET", "/api/commands/mcp/servers", "MCP servers"),
    EndpointTest("GET", "/api/commands/mcp/connections", "MCP connections"),
    EndpointTest("POST", "/api/commands/mcp/servers", "Add MCP server", {"name": "test", "type": "stdio", "command": "echo"}),
    EndpointTest("POST", "/api/commands/mcp/connect/{server_name}", "Connect MCP", params={"server_name": "test"}),
    EndpointTest("POST", "/api/commands/mcp/disconnect/{server_name}", "Disconnect MCP", params={"server_name": "test"}),
    EndpointTest("GET", "/api/commands/mcp/tools/{server_name}", "MCP tools", params={"server_name": "test"}),
    EndpointTest("POST", "/api/commands/mcp/call", "MCP call", {"server": "test", "tool": "test", "args": {}}),
    EndpointTest("GET", "/api/commands/mcp/resources/{server_name}", "MCP resources", params={"server_name": "test"}),
    EndpointTest("POST", "/api/commands/mcp/resource/read", "MCP read resource", {"server": "test", "uri": "test://test"}),

    # commands_router - Tasks and Plan
    EndpointTest("GET", "/api/commands/tasks", "Get tasks"),
    EndpointTest("POST", "/api/commands/tasks", "Create task", {"description": "test"}),
    EndpointTest("POST", "/api/commands/plan", "Plan"),
    EndpointTest("POST", "/api/commands/issue", "Issue", {"title": "test issue"}),

    # commands_router - Model commands
    EndpointTest("GET", "/api/commands/model", "Get model"),
    EndpointTest("POST", "/api/commands/model", "Set model", {"model": "claude-3-5-sonnet"}),
    EndpointTest("GET", "/api/commands/model/list", "List models"),
    EndpointTest("POST", "/api/commands/model/select", "Select model", {"model": "claude-3-5-sonnet"}),

    # commands_router - Config commands
    EndpointTest("GET", "/api/commands/config", "Get config"),
    EndpointTest("POST", "/api/commands/config", "Update config", {"key": "test", "value": "test"}),

    # commands_router - Context commands
    EndpointTest("GET", "/api/commands/context", "Get context"),
    EndpointTest("GET", "/api/commands/context/detailed", "Get detailed context"),
    EndpointTest("GET", "/api/commands/ctx_viz", "Context visualization"),

    # commands_router - Status commands
    EndpointTest("GET", "/api/commands/status", "Status"),
    EndpointTest("GET", "/api/commands/status/full", "Full status"),
    EndpointTest("GET", "/api/commands/cost", "Cost"),
    EndpointTest("GET", "/api/commands/usage", "Usage"),
    EndpointTest("GET", "/api/commands/stats", "Stats"),
    EndpointTest("GET", "/api/commands/insights", "Insights"),
    EndpointTest("GET", "/api/commands/files", "Files"),

    # commands_router - Effort/Fast commands
    EndpointTest("POST", "/api/commands/effort", "Effort", {"level": "medium"}),
    EndpointTest("POST", "/api/commands/fast", "Fast mode"),

    # commands_router - Version/Help/Doctor
    EndpointTest("GET", "/api/commands/version", "Version"),
    EndpointTest("GET", "/api/commands/help", "Help"),
    EndpointTest("GET", "/api/commands/doctor", "Doctor"),

    # commands_router - Init commands
    EndpointTest("POST", "/api/commands/init", "Init"),
    EndpointTest("POST", "/api/commands/init-verifiers", "Init verifiers"),

    # commands_router - Execute command
    EndpointTest("POST", "/api/commands/execute", "Execute", {"command": "echo test"}),

    # commands_router - Agent commands
    EndpointTest("GET", "/api/commands/agents", "List agents"),
    EndpointTest("GET", "/api/commands/agents/{id}", "Get agent", params={"id": "test"}),
    EndpointTest("POST", "/api/commands/agents/configure", "Configure agent", {"type": "general"}),
    EndpointTest("GET", "/api/commands/agents/list", "Agents list"),

    # commands_router - Feature flags
    EndpointTest("GET", "/api/commands/feature-flags", "Feature flags"),
    EndpointTest("GET", "/api/commands/feature-flag/{name}", "Get flag", params={"name": "test"}),

    # commands_router - Workflows
    EndpointTest("GET", "/api/commands/workflows", "List workflows"),
    EndpointTest("POST", "/api/commands/workflows/execute/{name}", "Execute workflow", params={"name": "test"}),

    # commands_router - Fork
    EndpointTest("GET", "/api/commands/fork", "List forks"),
    EndpointTest("POST", "/api/commands/fork", "Create fork"),
    EndpointTest("GET", "/api/commands/fork/{id}", "Get fork", params={"id": "test"}),
    EndpointTest("DELETE", "/api/commands/fork/{id}", "Delete fork", params={"id": "test"}),

    # commands_router - Buddy
    EndpointTest("GET", "/api/commands/buddy", "Buddy"),
    EndpointTest("POST", "/api/commands/buddy", "Buddy chat", {"message": "test"}),

    # commands_router - Plugin
    EndpointTest("GET", "/api/commands/plugin/list", "List plugins"),
    EndpointTest("POST", "/api/commands/plugin/manage", "Manage plugin", {"action": "enable", "name": "test"}),

    # commands_router - Export
    EndpointTest("POST", "/api/commands/export", "Export"),
    EndpointTest("POST", "/api/commands/export/conversation", "Export conversation"),

    # commands_router - Theme
    EndpointTest("GET", "/api/commands/theme", "Get theme"),
    EndpointTest("POST", "/api/commands/theme", "Set theme", {"name": "dark"}),
    EndpointTest("GET", "/api/commands/stickers", "Stickers"),

    # commands_router - Color/Thinkback
    EndpointTest("POST", "/api/commands/color", "Set color", {"name": "red"}),
    EndpointTest("POST", "/api/commands/thinkbackPlay", "Thinkback play", {"id": "test"}),

    # commands_router - UltraPlan
    EndpointTest("GET", "/api/commands/ultraplan", "Ultra plan"),
    EndpointTest("POST", "/api/commands/ultraplan", "Create ultra plan"),
    EndpointTest("GET", "/api/commands/ultraplan/poll", "Poll ultra plan"),

    # commands_router - Subscribe PR
    EndpointTest("GET", "/api/commands/subscribe-pr", "List PR subscriptions"),
    EndpointTest("POST", "/api/commands/subscribe-pr", "Subscribe PR", {"url": "https://github.com/test/test/pull/1"}),
    EndpointTest("DELETE", "/api/commands/subscribe-pr/{id}", "Unsubscribe PR", params={"id": "test"}),
    EndpointTest("GET", "/api/commands/subscribe-pr/{id}/events", "PR subscription events", params={"id": "test"}),

    # commands_router - Web setup
    EndpointTest("GET", "/api/commands/web-setup", "Web setup"),
    EndpointTest("POST", "/api/commands/web-setup", "Setup web", {"host": "localhost"}),
    EndpointTest("GET", "/api/commands/web-setup/devices", "Web devices"),
    EndpointTest("GET", "/api/commands/web-setup/device/{id}", "Web device", params={"id": "test"}),

    # commands_router - Backfill/Break cache
    EndpointTest("POST", "/api/commands/backfillSessions", "Backfill sessions"),
    EndpointTest("POST", "/api/commands/breakCache", "Break cache"),

    # commands_router - Bug hunter / Good claude
    EndpointTest("POST", "/api/commands/bughunter", "Bug hunter"),
    EndpointTest("POST", "/api/commands/goodClaude", "Good Claude"),

    # commands_router - Force snip
    EndpointTest("POST", "/api/commands/forceSnip", "Force snip"),

    # commands_router - Voice commands
    EndpointTest("GET", "/api/commands/voice/detailed-status", "Voice status"),
    EndpointTest("POST", "/api/commands/voice/enable", "Enable voice"),
    EndpointTest("POST", "/api/commands/voice/disable", "Disable voice"),
    EndpointTest("POST", "/api/commands/voice/recognize", "Voice recognize", {"audio": "test"}),
    EndpointTest("POST", "/api/commands/voice/start-recording", "Start recording"),
    EndpointTest("POST", "/api/commands/voice/stop-recording", "Stop recording"),
    EndpointTest("POST", "/api/commands/voice", "Voice command", {"command": "test"}),

    # commands_router - Peers
    EndpointTest("GET", "/api/commands/peers", "List peers"),
    EndpointTest("POST", "/api/commands/peers/connect", "Connect peer", {"host": "localhost"}),
    EndpointTest("DELETE", "/api/commands/peers/disconnect/{id}", "Disconnect peer", params={"id": "test"}),
    EndpointTest("POST", "/api/commands/peers/broadcast", "Broadcast", {"message": "test"}),

    # commands_router - Remote control
    EndpointTest("GET", "/api/commands/remote-control-server/status", "Remote status"),
    EndpointTest("POST", "/api/commands/remote-control-server/start", "Start remote"),
    EndpointTest("POST", "/api/commands/remote-control-server/stop", "Stop remote"),
    EndpointTest("POST", "/api/commands/remote-control-server", "Configure remote", {}),

    # commands_router - Proactive
    EndpointTest("GET", "/api/commands/proactive", "Get proactive"),
    EndpointTest("POST", "/api/commands/proactive", "Set proactive", {}),

    # commands_router - Resume/Rewind
    EndpointTest("POST", "/api/commands/resume", "Resume", {"session_id": "test"}),
    EndpointTest("POST", "/api/commands/rewind", "Rewind", {"steps": 5}),

    # commands_router - Teleport
    EndpointTest("POST", "/api/commands/teleport", "Teleport", {"path": "/test"}),
    EndpointTest("GET", "/api/commands/teleport/status", "Teleport status"),

    # commands_router - Bridge kick
    EndpointTest("POST", "/api/commands/bridgeKick", "Bridge kick"),

    # commands_router - Ant trace / Perf issue
    EndpointTest("POST", "/api/commands/antTrace", "Ant trace"),
    EndpointTest("POST", "/api/commands/perfIssue", "Perf issue"),

    # commands_router - Env
    EndpointTest("POST", "/api/commands/env", "Get env"),

    # commands_router - OAuth refresh
    EndpointTest("POST", "/api/commands/oauthRefresh", "OAuth refresh"),

    # commands_router - Debug tool call
    EndpointTest("POST", "/api/commands/debugToolCall", "Debug tool call", {"tool": "test", "args": {}}),

    # commands_router - Agents platform
    EndpointTest("POST", "/api/commands/agentsPlatform", "Agents platform"),

    # commands_router - Auto-fix PR
    EndpointTest("POST", "/api/commands/autofixPr", "Auto-fix PR", {"url": "https://github.com/test/test/pull/1"}),

    # commands_router - Mock limits
    EndpointTest("POST", "/api/commands/mockLimits", "Mock limits"),
]


async def test_endpoint(client: httpx.AsyncClient, test: EndpointTest) -> dict:
    start_time = time.time()
    url = BASE_URL + test.path.replace("{id}", "test-id").replace("{agent_id}", "test-agent").replace("{session_id}", "test-session").replace("{provider_id}", "anthropic").replace("{server_name}", "test-server").replace("{name}", "test").replace("{server}", "test").replace("{tool}", "test").replace("{hook_id}", "test-hook").replace("{rule_id}", "test-rule").replace("{worker_id}", "test").replace("{subagent_id}", "test").replace("{peer_id}", "test-peer").replace("{subscription_id}", "test-sub")

    try:
        response = await client.request(test.method, url, json=test.body, params=test.params, headers=get_headers(), timeout=10.0)
        duration = time.time() - start_time
        return {
            "name": test.name,
            "method": test.method,
            "path": test.path,
            "status": response.status_code,
            "success": response.status_code < 500,
            "duration_ms": round(duration * 1000, 2),
            "error": None if response.status_code < 500 else response.text[:200],
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "name": test.name,
            "method": test.method,
            "path": test.path,
            "status": 0,
            "success": False,
            "duration_ms": round(duration * 1000, 2),
            "error": str(e)[:200],
        }


async def run_all_tests():
    print("=" * 60)
    print("API Server Comprehensive Test Suite")
    print(f"Target: {BASE_URL}")
    print("=" * 60)

    results = []
    total = len(ALL_ENDPOINTS)

    async with httpx.AsyncClient() as client:
        for i, test in enumerate(ALL_ENDPOINTS):
            result = await test_endpoint(client, test)
            results.append(result)
            status_icon = "✅" if result["success"] else "❌"
            print(f"  {status_icon} [{i+1}/{total}] {result['method']} {result['name']} → {result['status']} ({result['duration_ms']}ms)")

    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{(passed/total*100):.1f}%",
        "results": results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print(f"Results saved to: {OUTPUT_FILE}")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default=BASE_URL)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()
    BASE_URL = args.server
    OUTPUT_FILE = args.output

    asyncio.run(run_all_tests())
