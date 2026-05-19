# Test 19: Read Multiple Files

## Task for Agent
Read both `app.py` and `requirements.txt` from `python-api` and summarize what the project does.
Path: `C:\Users\enoma\Desktop\cato-test\projects\python-api`

Files to read:
- app.py
- requirements.txt

## Expected Result
- Identifies it as a Flask API project
- Lists the dependencies (flask, flask-cors)
- Describes the API endpoint (/api/hello)

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\app.py"
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\requirements.txt"
```