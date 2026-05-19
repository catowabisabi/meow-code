# Test 12: Batch File Creation

## Task for Agent
Create 3 new files in `docs-site`:
Path: `C:\Users\enoma\Desktop\cato-test\projects\docs-site`

1. `info.txt` with content: "Project info"
2. `version.txt` with content: "Version: 1.0.0"
3. `status.txt` with content: "Status: Active"

## Expected Result
- All 3 files exist with correct content

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\info.txt"
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\version.txt"
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\status.txt"
```

## Expected Output
```
Project info
Version: 1.0.0
Status: Active
```