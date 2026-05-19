# Task DL-19: Find Large Files

## Task
Search for the 3 largest files in `projects` folder and list them with their sizes.

Location: `C:\Users\enoma\Desktop\cato-test\projects`

## Verification
Manual check - run: Get-ChildItem -Recurse | Sort-Object Length -Descending | Select-Object -First 3