# Test 7: Code Search - Find Keyword

## Task for Agent
Search for all files in `python-api/` that contain the word "Flask" (case-insensitive).
Path: `C:\Users\enoma\Desktop\cato-test\projects\python-api`

List the files and show the matching lines.

## Expected Result
- File: app.py contains "Flask"

## Verification Command
```powershell
Select-String -Path "C:\Users\enoma\Desktop\cato-test\projects\python-api\*.py" -Pattern "Flask" -CaseSensitive:$false
```

## Expected Output
```
C:\Users\enoma\Desktop\cato-test\projects\python-api\app.py:2:from flask import Flask, jsonify
```