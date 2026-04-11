#!/usr/bin/env python3
"""
API Server Test Script
Usage: python test_api.py [--server http://localhost:8000]
"""

import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000"


def get_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "X-API-Key": "test-key",
    }


async def test_sessions():
    print("\n📋 Testing Sessions...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/sessions", headers=get_headers())
    print(f"  GET /api/sessions → {r.status_code}")
    
    r = await httpx.AsyncClient().post(
        f"{BASE_URL}/api/sessions",
        headers=get_headers(),
        json={"model": "claude-3-5-sonnet", "provider": "anthropic"}
    )
    print(f"  POST /api/sessions → {r.status_code}")
    if r.status_code == 200:
        session_id = r.json().get("id")
        print(f"    Created session: {session_id}")
        
        r = await httpx.AsyncClient().get(f"{BASE_URL}/api/sessions/{session_id}", headers=get_headers())
        print(f"  GET /api/sessions/{session_id[:8]}... → {r.status_code}")
        
        r = await httpx.AsyncClient().post(f"{BASE_URL}/api/sessions/{session_id}/save", headers=get_headers())
        print(f"  POST /api/sessions/{session_id[:8]}.../save → {r.status_code}")
        
        r = await httpx.AsyncClient().delete(f"{BASE_URL}/api/sessions/{session_id}", headers=get_headers())
        print(f"  DELETE /api/sessions/{session_id[:8]}... → {r.status_code}")
    
    return True


async def test_tools():
    print("\n🔧 Testing Tools...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/tools", headers=get_headers())
    print(f"  GET /api/tools → {r.status_code}")
    if r.status_code == 200:
        tools = r.json().get("tools", [])
        print(f"    Found {len(tools)} tools")


async def test_shell():
    print("\n🐚 Testing Shell...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/shell/cwd", headers=get_headers())
    print(f"  GET /api/shell/cwd → {r.status_code}")
    if r.status_code == 200:
        print(f"    CWD: {r.json().get('cwd', 'N/A')}")
    
    r = await httpx.AsyncClient().post(
        f"{BASE_URL}/api/shell",
        headers=get_headers(),
        json={"command": "echo 'hello from api'", "timeout": 5000}
    )
    print(f"  POST /api/shell → {r.status_code}")
    if r.status_code == 200:
        print(f"    Output: {r.json().get('output', 'N/A')[:50]}...")


async def test_mcp():
    print("\n🔌 Testing MCP...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/commands/mcp/servers", headers=get_headers())
    print(f"  GET /api/commands/mcp/servers → {r.status_code}")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/commands/mcp/connections", headers=get_headers())
    print(f"  GET /api/commands/mcp/connections → {r.status_code}")


async def test_git():
    print("\n📦 Testing Git...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/commands/git/status", headers=get_headers())
    print(f"  GET /api/commands/git/status → {r.status_code}")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/commands/git/branch", headers=get_headers())
    print(f"  GET /api/commands/git/branch → {r.status_code}")


async def test_models():
    print("\n🤖 Testing Models...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/models", headers=get_headers())
    print(f"  GET /api/models → {r.status_code}")
    if r.status_code == 200:
        models = r.json().get("models", [])
        print(f"    Found {len(models)} configured models")


async def test_skills():
    print("\n✨ Testing Skills...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/skills", headers=get_headers())
    print(f"  GET /api/skills → {r.status_code}")
    if r.status_code == 200:
        skills = r.json().get("skills", [])
        print(f"    Found {len(skills)} skills")


async def test_permissions():
    print("\n🔐 Testing Permissions...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/permissions", headers=get_headers())
    print(f"  GET /api/permissions → {r.status_code}")
    if r.status_code == 200:
        rules = r.json()
        print(f"    Found {len(rules)} permission rules")


async def test_agents():
    print("\n🤖 Testing Agents...")
    
    agent_id = "test-agent-001"
    
    r = await httpx.AsyncClient().post(
        f"{BASE_URL}/api/agents/{agent_id}/summary/start",
        headers=get_headers()
    )
    print(f"  POST /api/agents/{agent_id}/summary/start → {r.status_code}")
    
    r = await httpx.AsyncClient().get(
        f"{BASE_URL}/api/agents/{agent_id}/summary",
        headers=get_headers()
    )
    print(f"  GET /api/agents/{agent_id}/summary → {r.status_code}")
    
    r = await httpx.AsyncClient().delete(
        f"{BASE_URL}/api/agents/{agent_id}/summary/stop",
        headers=get_headers()
    )
    print(f"  DELETE /api/agents/{agent_id}/summary/stop → {r.status_code}")


async def test_hooks():
    print("\n🪝 Testing Hooks...")
    
    r = await httpx.AsyncClient().get(f"{BASE_URL}/api/hooks", headers=get_headers())
    print(f"  GET /api/hooks → {r.status_code}")


async def run_all_tests():
    print("=" * 60)
    print("API Server Test Suite")
    print("=" * 60)
    
    try:
        await test_sessions()
        await test_tools()
        await test_shell()
        await test_mcp()
        await test_git()
        await test_models()
        await test_skills()
        await test_permissions()
        await test_agents()
        await test_hooks()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except httpx.ConnectError:
        print(f"\n❌ Cannot connect to {BASE_URL}")
        print("   Make sure the API server is running:")
        print("   uvicorn api_server.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://localhost:8000")
    args = parser.parse_args()
    BASE_URL = args.server
    
    asyncio.run(run_all_tests())
