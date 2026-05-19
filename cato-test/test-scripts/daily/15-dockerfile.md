# Task DL-15: Create Docker Config

## Task
Create `Dockerfile` in `python-api`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\python-api\Dockerfile`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\Dockerfile"
```