# Task DL-20: Find Recently Modified

## Task
List all files modified in the last 24 hours in the `projects` folder.

Location: `C:\Users\enoma\Desktop\cato-test\projects`

## Verification
```powershell
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects" -Recurse | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) }
```