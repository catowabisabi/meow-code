# Test 20: Verify File Existence

## Task for Agent
Check if these files exist and report their status:
Path base: `C:\Users\enoma\Desktop\cato-test\projects`

1. `hello-world/package.json`
2. `python-api/app.py`
3. `react-app/package.json`
4. `docs-site/README.md`

For each file, tell me if it exists or not.

## Expected Result
All 4 files should exist:
- ✅ hello-world/package.json
- ✅ python-api/app.py
- ✅ react-app/package.json
- ✅ docs-site/README.md

## Verification Command
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\package.json"
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\python-api\app.py"
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\react-app\package.json"
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\docs-site\README.md"
```

## Expected Output
All should return: True