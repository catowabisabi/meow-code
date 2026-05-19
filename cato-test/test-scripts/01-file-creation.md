# Test 1: File Creation

## Task for Agent
Create a new file called `hello.txt` in the `hello-world` project folder.
The file should be located at: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt`

Content of the file:
```
Hello World
This is a test file.
```

## Expected Result
- File exists at `C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt`
- Content matches exactly

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"
```

## Expected Output
```
Hello World
This is a test file.
```