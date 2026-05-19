# Test 18: Directory Listing

## Task for Agent
List all directories in `projects/`.
Path: `C:\Users\enoma\Desktop\cato-test\projects`

List only directories, not files.

## Expected Result
- hello-world
- python-api
- react-app
- docs-site

## Verification Command
```powershell
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects" -Directory | Select-Object Name
```

## Expected Output
```
hello-world
python-api
react-app
docs-site
```