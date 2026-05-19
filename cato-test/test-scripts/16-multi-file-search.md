# Test 16: Multi-Project Search

## Task for Agent
Search all projects for files that contain the word "Hello" (case-insensitive).
Search in: `C:\Users\enoma\Desktop\cato-test\projects`

List all matching files and the lines that contain "Hello".

## Expected Result
Files likely to contain "Hello":
- hello-world/index.js (console.log('Hello World!'))
- react-app/src/App.jsx (<h1>Hello React</h1>)
- docs-site/README.md (# Hello Docs)

## Verification Command
```powershell
Select-String -Path "C:\Users\enoma\Desktop\cato-test\projects\**" -Pattern "Hello" -CaseSensitive:$false
```

## Notes
- This tests searching across multiple projects
- May need recursive search enabled