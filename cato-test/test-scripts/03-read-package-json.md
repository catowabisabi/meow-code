# Test 3: Read Package.json

## Task for Agent
Read the `package.json` file in the `react-app` project.
Path: `C:\Users\enoma\Desktop\cato-test\projects\react-app\package.json`

List all dependencies and devDependencies with their versions.

## Expected Result
Should list:
- dependencies: react, react-dom
- devDependencies: @vitejs/plugin-react, vite

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\react-app\package.json" | ConvertFrom-Json | Select-Object -ExpandProperty dependencies
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\react-app\package.json" | ConvertFrom-Json | Select-Object -ExpandProperty devDependencies
```

## Expected Output
```
Name                           Value
----                           -----
react                          ^18.2.0
react-dom                      ^18.2.0

Name                           Value
----                           -----
@vitejs/plugin-react           ^4.2.0
vite                           ^5.0.0
```