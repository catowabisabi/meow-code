# Test 17: File Type Search

## Task for Agent
Find all `.jsx` files in the `react-app` project.
Path: `C:\Users\enoma\Desktop\cato-test\projects\react-app`

List all files with .jsx extension and their paths.

## Expected Result
- src/main.jsx
- src/App.jsx

## Verification Command
```powershell
Get-ChildItem -Path "C:\Users\enoma\Desktop\cato-test\projects\react-app" -Recurse -Include "*.jsx"
```

## Expected Output
```
    Directory: C:\Users\enoma\Desktop\cato-test\projects\react-app\src

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          5/4/2026      1:27           App.jsx
-a----          5/4/2026      1:27          main.jsx
```