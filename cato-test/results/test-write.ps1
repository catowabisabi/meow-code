$body = @{
    path = "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"
    content = "Hello World"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri 'http://localhost:7778/api/files/write' -Method POST -ContentType 'application/json' -Body $body
Write-Host "Response: $($response | ConvertTo-Json)"