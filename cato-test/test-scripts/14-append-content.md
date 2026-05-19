# Test 14: Append to File

## Task for Agent
Append the following text to `README.md` in `hello-world`:
Path: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\README.md`

Append this line at the end:
```
Last updated: 2026-05-04
```

## Expected Result
- Original content preserved
- New line appended

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\README.md"
```

## Expected Output
```
# Hello World

A simple test project.
Last updated: 2026-05-04
```