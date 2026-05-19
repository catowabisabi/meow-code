# Task DL-7: Create a Python Test File

## Task
Create `test_app.py` in `python-api`:
```python
import pytest
from app import app

def test_hello():
    client = app.test_client()
    response = client.get('/api/hello')
    assert response.status_code == 200
```

Location: `C:\Users\enoma\Desktop\cato-test\projects\python-api\test_app.py`

## Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\test_app.py"
```