# Test WebSocket Streaming
# This script tests WebSocket chat functionality

$ErrorActionPreference = "Continue"
Write-Host "=== WebSocket Streaming Test ===" -ForegroundColor Cyan

# Create a new session first
Write-Host "`n[1] Creating test session..." -ForegroundColor Yellow
try {
    $session = Invoke-RestMethod -Uri 'http://localhost:7778/api/sessions' -Method POST -ContentType 'application/json'
    $sessionId = $session.id
    Write-Host "  Session ID: $sessionId" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Could not create session: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test WebSocket connection
Write-Host "`n[2] Testing WebSocket connection..." -ForegroundColor Yellow

$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cancellationToken = [Threading.CancellationToken]::None

try {
    $ws.ConnectAsync(([Uri]"ws://localhost:7778/ws/chat?sessionId=$sessionId"), $cancellationToken).Wait()
    Write-Host "  WebSocket connected!" -ForegroundColor Green

    # Send a simple chat message
    $message = @{
        type = "chat"
        content = @{
            role = "user"
            content = @(@{ type = "text"; text = "Hello, respond with 'Hi!'" })
        }
        stream = $true
    } | ConvertTo-Json -Compress

    $msgBytes = [Text.Encoding]::UTF8.GetBytes($message)
    $arraySegment = [ArraySegment[byte]]::new($msgBytes)
    $ws.SendAsync($arraySegment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cancellationToken).Wait()
    Write-Host "  Message sent!" -ForegroundColor Green

    # Receive responses
    $receivedMessages = @()
    $timeout = 30  # seconds
    $endTime = (Get-Date).AddSeconds($timeout)

    Write-Host "  Waiting for response (timeout: $timeout seconds)..." -ForegroundColor Gray

    while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open -and (Get-Date) -lt $endTime) {
        $buffer = [byte[]]::new(4096)
        $segment = [ArraySegment[byte]]::new($buffer)
        $result = $ws.ReceiveAsync($segment, $cancellationToken)

        if ($result.Wait(5000) -and $result.Result.Count -gt 0) {
            $text = [Text.Encoding]::UTF8.GetString($buffer, 0, $result.Result.Count)
            $receivedMessages += $text
            Write-Host "    Received: $($text.Substring(0, [Math]::Min(100, $text.Length)))..." -ForegroundColor Gray
        }
    }

    if ($receivedMessages.Count -gt 0) {
        Write-Host "  Received $($receivedMessages.Count) messages" -ForegroundColor Green
        Write-Host "  [PASS]" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] No messages received" -ForegroundColor Red
    }

    # Close WebSocket
    $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Done", $cancellationToken).Wait()
    Write-Host "  WebSocket closed" -ForegroundColor Green

} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if ($ws) {
        $ws.Dispose()
    }
}

# Cleanup - delete the test session
Write-Host "`n[3] Cleaning up test session..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "http://localhost:7778/api/sessions/$sessionId" -Method DELETE | Out-Null
    Write-Host "  Session deleted" -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not delete session: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n=== WebSocket Test Complete ===" -ForegroundColor Cyan
