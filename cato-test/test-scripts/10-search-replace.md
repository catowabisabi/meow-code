# Test 10: Search and Replace

## Task for Agent
In the `docs-site` project, find all `.md` files that contain the word "TODO" and replace it with "TASKS".
Path: `C:\Users\enoma\Desktop\cato-test\projects\docs-site`

Replace "TODO" with "TASKS" in all markdown files.

## Expected Result
- Files are modified
- TODO → TASKS in all .md files

## Verification Command
```powershell
Select-String -Path "C:\Users\enoma\Desktop\cato-test\projects\docs-site\*.md" -Pattern "TASKS"
```

## Expected Output
```
C:\Users\enoma\Desktop\cato-test\projects\docs-site\TODO.md:# TASKS
C:\Users\enoma\Desktop\cato-test\projects\docs-site\TODO.md:- [ ] First task
C:\Users\enoma\Desktop\cato-test\projects\docs-site\TODO.md:- [ ] Second task
```

## Notes
- The file is renamed TODO.md but content changed from TODO to TASKS