# Test 6: Git Status

## Task for Agent
Run `git status` in the `hello-world` project folder.
Path: `C:\Users\enoma\Desktop\cato-test\projects\hello-world`

Tell me what files are shown as untracked.

## Expected Result
Files shown as untracked:
- index.js
- package.json
- README.md

## Verification Command
```powershell
Set-Location "C:\Users\enoma\Desktop\cato-test\projects\hello-world"
git status --porcelain
```

## Expected Output
```
?? README.md
?? index.js
?? package.json
```

## Notes
- Requires Test 5 (git init) to be run first
- ?? means untracked files