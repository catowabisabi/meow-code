# Test 11: File Deletion

## Task for Agent
Delete the file `hello.txt` in `hello-world` that we created in Test 1.
Path: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt`

## Expected Result
- File no longer exists

## Verification Command
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"
```

## Expected Output
```
False
```

## Notes
- Requires Test 1 to be run first