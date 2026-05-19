# Cato-Claude API Comprehensive Test Suite

## Server Status
- Backend: http://localhost:7778 ✅ Running
- Frontend: http://localhost:7777 ✅ Running

---

## Test Scripts

### 1. Sessions API Tests

```powershell
# Test 1: Create session
$body = @{ model="gpt-4o"; provider="openai" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/sessions' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Create session: $($r | ConvertTo-Json)"

# Test 2: List sessions
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/sessions' -Method GET
Write-Host "List sessions: $($r | ConvertTo-Json)"

# Test 3: Get session by ID
$sessionId = $r.sessions[0].id
$r = Invoke-RestMethod -Uri "http://localhost:7778/api/sessions/$sessionId" -Method GET
Write-Host "Get session: $($r | ConvertTo-Json)"

# Test 4: Update session title
$body = @{ title="Test Session" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "http://localhost:7778/api/sessions/$sessionId" -Method PUT -ContentType 'application/json' -Body $body
Write-Host "Update title: $($r | ConvertTo-Json)"

# Test 5: Delete session
$r = Invoke-RestMethod -Uri "http://localhost:7778/api/sessions/$sessionId" -Method DELETE
Write-Host "Delete session: $($r | ConvertTo-Json)"
```

### 2. Skills API Tests

```powershell
# Test 1: List all skills
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/skills' -Method GET
Write-Host "List skills: $($r | ConvertTo-Json)"

# Test 2: Execute skill
$body = @{ name="hello-world"; args="test" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/skills/execute' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Execute skill: $($r | ConvertTo-Json)"

# Test 3: Create skill
$body = @{
    name="test-skill"
    prompt="You are a test skill"
    triggers=@("test")
} | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/skills' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Create skill: $($r | ConvertTo-Json)"

# Test 4: Update skill
$body = @{ description="Updated description" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/skills/test-skill' -Method PUT -ContentType 'application/json' -Body $body
Write-Host "Update skill: $($r | ConvertTo-Json)"

# Test 5: Delete skill
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/skills/test-skill' -Method DELETE
Write-Host "Delete skill: $($r | ConvertTo-Json)"
```

### 3. Models API Tests

```powershell
# Test 1: List models
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/models' -Method GET
Write-Host "List models: $($r | ConvertTo-Json)"

# Test 2: Get model config
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/models/config' -Method GET
Write-Host "Model config: $($r | ConvertTo-Json)"
```

### 4. Memory API Tests

```powershell
# Test 1: Search memory
$body = @{ query="test query" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/memory/search' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Search memory: $($r | ConvertTo-Json)"

# Test 2: Add memory
$body = @{
    type="note"
    content="Test memory content"
    metadata=@{}
} | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/memory' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Add memory: $($r | ConvertTo-Json)"

# Test 3: List memories
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/memory' -Method GET
Write-Host "List memories: $($r | ConvertTo-Json)"
```

### 5. Shell API Tests

```powershell
# Test 1: Execute shell command
$body = @{ command="echo Hello"; cwd="C:\Users\enoma\Desktop\cato-test" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/shell' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Shell output: $($r | ConvertTo-Json)"
```

### 6. MCP API Tests

```powershell
# Test 1: List MCP servers
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/mcp/servers' -Method GET
Write-Host "MCP servers: $($r | ConvertTo-Json)"

# Test 2: Get MCP templates
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/mcp/templates' -Method GET
Write-Host "MCP templates: $($r | ConvertTo-Json)"

# Test 3: Create MCP server
$body = @{
    name="test-mcp"
    command="npx"
    args=@("-y", "some-server")
} | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/mcp/servers' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Create MCP server: $($r | ConvertTo-Json)"

# Test 4: Delete MCP server
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/mcp/servers/test-mcp' -Method DELETE
Write-Host "Delete MCP server: $($r | ConvertTo-Json)"
```

### 7. Database API Tests

```powershell
# Test 1: List database entries
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/database' -Method GET
Write-Host "Database: $($r | ConvertTo-Json)"

# Test 2: Query database
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/database?query=test' -Method GET
Write-Host "Database query: $($r | ConvertTo-Json)"
```

### 8. Settings API Tests

```powershell
# Test 1: Get settings
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/settings' -Method GET
Write-Host "Settings: $($r | ConvertTo-Json)"

# Test 2: Update settings
$body = @{ theme="dark"; language="en" } | ConvertTo-Json
$r = Invoke-RestMethod -Uri 'http://localhost:7778/api/settings' -Method PUT -ContentType 'application/json' -Body $body
Write-Host "Update settings: $($r | ConvertTo-Json)"
```

---

## Running All Tests

Save as `run-all-tests.ps1` and execute:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\enoma\Desktop\cato-test\results\run-all-tests.ps1"
```

## Expected Duration
- All tests: ~5-10 minutes
- Individual API tests: ~30 seconds each