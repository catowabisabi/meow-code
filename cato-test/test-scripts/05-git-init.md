# Test 5: Git Initialization

## Task for Agent
Initialize a git repository in the `hello-world` project folder.
Path: `C:\Users\enoma\Desktop\cato-test\projects\hello-world`

Run: `git init`

## Expected Result
- `.git` folder is created
- Repository is ready for commits

## Verification Command
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\.git"
```

## Expected Output
```
True
```

## Notes
- This test requires git to be installed
- The repo starts with no commits