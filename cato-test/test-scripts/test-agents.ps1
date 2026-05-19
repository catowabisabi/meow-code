# Test Agent Spawning API
Write-Host "=== Testing Agent API ===" -ForegroundColor Cyan

# 1. List all agents
Write-Host "`n[1] List all agents [GET /api/agents]" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:7778/api/agents' -Method GET
    Write-Host "  Count: $($response.count)"
    Write-Host "  [PASS]" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Spawn a new agent
Write-Host "`n[2] Spawn new agent [POST /api/agents]" -ForegroundColor Yellow
try {
    $body = @{
        name = "test-explorer"
        type = "explore"
        task = "List files in current directory"
        sessionId = "webui"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri 'http://localhost:7778/api/agents' -Method POST -ContentType 'application/json' -Body $body
    $agentId = $response.agent.id
    Write-Host "  Agent ID: $agentId"
    Write-Host "  [PASS]" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $agentId = $null
}

# 3. Get specific agent
if ($agentId) {
    Write-Host "`n[3] Get agent [GET /api/agents/$agentId]" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:7778/api/agents/$agentId" -Method GET
        Write-Host "  Agent name: $($response.agent.name)"
        Write-Host "  Agent type: $($response.agent.type)"
        Write-Host "  [PASS]" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 4. List agents again
Write-Host "`n[4] List agents again [GET /api/agents]" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:7778/api/agents' -Method GET
    Write-Host "  Count: $($response.count)"
    Write-Host "  [PASS]" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Delete agent
if ($agentId) {
    Write-Host "`n[5] Delete agent [DELETE /api/agents/$agentId]" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:7778/api/agents/$agentId" -Method DELETE
        Write-Host "  [PASS]" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 6. Verify deletion
Write-Host "`n[6] Verify deletion [GET /api/agents]" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:7778/api/agents' -Method GET
    Write-Host "  Count: $($response.count)"
    if ($response.count -eq 0) {
        Write-Host "  [PASS]" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Agent still exists" -ForegroundColor Red
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Agent API Tests Complete ===" -ForegroundColor Cyan
