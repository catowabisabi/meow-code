# Task DL-25: Create a Cron Script

## Task
Create `cron.sh` in `hello-world`:
```bash
#!/bin/bash
# Daily backup script
DATE=$(date +%Y-%m-%d)
echo "Running backup for $DATE"
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\hello-world\cron.sh`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\cron.sh"
```