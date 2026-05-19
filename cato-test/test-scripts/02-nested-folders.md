# Test 2: Nested Folder Creation

## Task for Agent
Create a nested folder structure `a/b/c/d.txt` in the `docs-site` project.
Full path: `C:\Users\enoma\Desktop\cato-test\projects\docs-site\a\b\c\d.txt`

Content of d.txt:
```
Deep nested file
```

## Expected Result
- Folder structure: `docs-site/a/b/c/d.txt` exists
- File contains "Deep nested file"

## Verification Command
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\docs-site\a\b\c\d.txt"
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\a\b\c\d.txt"
```

## Expected Output
```
True
Deep nested file
```