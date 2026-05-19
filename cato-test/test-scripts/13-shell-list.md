# Test 13: Shell Command - List Files

## Task for Agent
Run a shell command to list all files (excluding hidden) in the `projects` folder.
Path: `C:\Users\enoma\Desktop\cato-test\projects`

Use: `ls -la` or `dir` to list all files

## Expected Result
- Lists all project folders

## Verification Command
```powershell
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects" -Directory
```

## Expected Output
```
    Directory: C:\Users\enoma\Desktop\cato-test\projects

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          5/4/2026      1:27                hello-world
d-----          5/4/2026      1:27                python-api
d-----           ...                react-app
d-----          5/4/2026      1:27                docs-site
```