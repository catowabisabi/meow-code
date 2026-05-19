# Test 15: Create Python File

## Task for Agent
Create a new file `utils.py` in `python-api` with this content:
Path: `C:\Users\enoma\Desktop\cato-test\projects\python-api\utils.py`

```python
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
```

## Expected Result
- File exists with both functions

## Verification Command
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\utils.py"
```

## Expected Output
```
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
```