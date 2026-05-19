# Task DL-5: Create a Project Backup Script

## Task
Create a file `backup.bat` in `hello-world`:
```batch
@echo off
echo Backing up project...
xcopy /E /I /Y *.js backup\
xcopy /E /I /Y *.json backup\
echo Backup complete!
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\backup.bat`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\backup.bat"
```