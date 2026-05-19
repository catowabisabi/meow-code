# Test 8: Count Lines of Code

## Task for Agent
Count the total lines of code in the `react-app/src` folder.
Path: `C:\Users\enoma\Desktop\cato-test\projects\react-app\src`

Report the total line count.

## Expected Result
- Total lines > 10 (we have main.jsx and App.jsx)

## Verification Command
```powershell
(Get-ChildItem -Path "C:\Users\enoma\Desktop\cato-test\projects\react-app\src" -Recurse -File | Get-Content | Measure-Object -Line).Lines
```

## Expected Output
A number greater than 10

## Notes
- main.jsx has ~7 lines
- App.jsx has ~3 lines
- Total should be around 10+