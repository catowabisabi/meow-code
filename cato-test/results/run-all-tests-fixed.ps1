# Cato-Claude API FIXED Test Runner
# Tests all major API endpoints with CORRECT endpoints

$ErrorActionPreference = "Continue"
$results = @()

function Test-API {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )

    $result = @{
        Name = $Name
        Method = $Method
        Endpoint = $Endpoint
        Status = "PASS"
        Error = $null
        Response = $null
    }

    try {
        $uri = "http://localhost:7778$Endpoint"
        $params = @{
            Method = $Method
            ContentType = "application/json"
        }

        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Compress)
        }

        $response = Invoke-RestMethod -Uri $uri @params -ErrorAction Stop
        $result.Response = $response
    }
    catch {
        $result.Status = "FAIL"
        $result.Error = $_.Exception.Message
    }

    return $result
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cato-Claude API Test Suite (FIXED)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. Sessions API Tests
# ========================================
Write-Host "[1] Testing Sessions API..." -ForegroundColor Yellow

$results += Test-API -Name "Create Session" -Method POST -Endpoint "/api/sessions" -Body @{ model="gpt-4o"; provider="openai" }
$results += Test-API -Name "List Sessions" -Method GET -Endpoint "/api/sessions"

# ========================================
# 2. Files API Tests
# ========================================
Write-Host "[2] Testing Files API..." -ForegroundColor Yellow

$results += Test-API -Name "List Files (test folder)" -Method GET -Endpoint "/api/files?path=C:\Users\enoma\Desktop\cato-test"
$results += Test-API -Name "Read File (hello.txt)" -Method GET -Endpoint "/api/files/read?path=C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"
$results += Test-API -Name "Write New File" -Method POST -Endpoint "/api/files/write" -Body @{
    path = "C:\Users\enoma\Desktop\cato-test\projects\hello-world\test-created.txt"
    content = "Created via API test"
}

# ========================================
# 3. Skills API Tests
# ========================================
Write-Host "[3] Testing Skills API..." -ForegroundColor Yellow

$results += Test-API -Name "List Skills" -Method GET -Endpoint "/api/skills"

# ========================================
# 4. Models API Tests
# ========================================
Write-Host "[4] Testing Models API..." -ForegroundColor Yellow

$results += Test-API -Name "List Models" -Method GET -Endpoint "/api/models"

# ========================================
# 5. MCP API Tests
# ========================================
Write-Host "[5] Testing MCP API..." -ForegroundColor Yellow

$results += Test-API -Name "List MCP Servers" -Method GET -Endpoint "/api/mcp/servers"
$results += Test-API -Name "Get MCP Templates" -Method GET -Endpoint "/api/mcp/templates"

# ========================================
# 6. Memory API Tests (FIXED: GET not POST)
# ========================================
Write-Host "[6] Testing Memory API..." -ForegroundColor Yellow

$results += Test-API -Name "List Memories" -Method GET -Endpoint "/api/memory"
$results += Test-API -Name "Search Memory (GET)" -Method GET -Endpoint "/api/memory/search?q=test"

# ========================================
# 7. Databases API Tests (FIXED: /databases not /database)
# ========================================
Write-Host "[7] Testing Databases API..." -ForegroundColor Yellow

$results += Test-API -Name "List Databases" -Method GET -Endpoint "/api/databases"

# ========================================
# 8. Settings API Tests
# ========================================
Write-Host "[8] Testing Settings API..." -ForegroundColor Yellow

$results += Test-API -Name "Get Settings" -Method GET -Endpoint "/api/settings"

# ========================================
# 9. Shell API Test
# ========================================
Write-Host "[9] Testing Shell API..." -ForegroundColor Yellow

$results += Test-API -Name "Execute Shell" -Method POST -Endpoint "/api/shell" -Body @{
    command = "echo Hello from shell"
    cwd = "C:\Users\enoma\Desktop\cato-test"
}

# ========================================
# Summary
# ========================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count

Write-Host ""
Write-Host "Total Tests: $($results.Count)" -ForegroundColor White
Write-Host "Passed: $passCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor Red
Write-Host ""

# Save results
$results | ForEach-Object {
    $status = if ($_.Status -eq "PASS") { "PASS" } else { "FAIL" }
    Write-Host "[$status] $($_.Name) [$($_.Method) $($_.Endpoint)]"

    if ($_.Status -eq "FAIL") {
        Write-Host "   Error: $($_.Error)" -ForegroundColor Red
    }
}

# Save to file
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$results | ConvertTo-Json -Depth 5 | Out-File "C:\Users\enoma\Desktop\cato-test\results\test-results-$timestamp.json"

Write-Host ""
Write-Host "Results saved to: C:\Users\enoma\Desktop\cato-test\results\test-results-$timestamp.json" -ForegroundColor Gray