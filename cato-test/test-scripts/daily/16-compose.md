# Task DL-16: Create Docker Compose

## Task
Create `docker-compose.yml` in `python-api`:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\python-api\docker-compose.yml`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\docker-compose.yml"
```