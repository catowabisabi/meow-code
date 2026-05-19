# Real-Life Daily Tasks - Agent API Testing

These are practical, everyday tasks that simulate real usage scenarios.

---

## 📝 Writing & Documentation

### Task DL-1: Write a Meeting Note
**File**: `daily\01-meeting-notes.md`

### Task
Create a meeting note file `meeting-2026-05-04.md` in `docs-site` with this structure:
```markdown
# Meeting Notes - 2026-05-04

## Attendees
- Alice
- Bob
- Charlie

## Agenda
1. Project status update
2. Budget review
3. Next steps

## Notes
- Project is on track
- Budget approved for Q2

## Action Items
- [ ] Alice: Send report
- [ ] Bob: Schedule follow-up
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\meeting-2026-05-04.md"
```

---

### Task DL-2: Update README
**File**: `daily\02-update-readme.md`

### Task
Update the README.md in `hello-world` to add a "Installation" section at the end:
```markdown

## Installation

```bash
npm install
npm start
```
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\README.md"
```

---

### Task DL-3: Create a Changelog Entry
**File**: `daily\03-changelog.md`

### Task
Create a new file `CHANGELOG.md` in `hello-world` with:
```markdown
# Changelog

## [1.0.1] - 2026-05-04
### Added
- Documentation updates

## [1.0.0] - 2026-05-01
### Added
- Initial release
- Hello World functionality
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\CHANGELOG.md"
```

---

## 🗂️ File Organization

### Task DL-4: Sort Files by Type
**File**: `daily\04-sort-files.md`

### Task
In the `docs-site` folder, create two new folders:
- `markdown/` - move all `.md` files here
- `text/` - create a new file `notes.txt` with "Sorted files"

### Verification
```powershell
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects\docs-site\markdown"
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects\docs-site\text\notes.txt"
```

---

### Task DL-5: Create a Project Backup Script
**File**: `daily\05-backup-script.md`

### Task
Create a file `backup.bat` in `hello-world`:
```batch
@echo off
echo Backing up project...
xcopy /E /I /Y *.js backup\
xcopy /E /I /Y *.json backup\
echo Backup complete!
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\backup.bat"
```

---

## 🔧 Development Tasks

### Task DL-6: Add npm Script
**File**: `daily\06-add-script.md`

### Task
Add a new script to `hello-world/package.json`:
- Script name: `"backup": "node backup.js"`
- Create a placeholder file `backup.js` with:
```javascript
console.log('Backup functionality');
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\package.json" | ConvertFrom-Json | Select-Object -ExpandProperty scripts
```

---

### Task DL-7: Create a Python Test File
**File**: `daily\07-python-test.md`

### Task
Create `test_app.py` in `python-api`:
```python
import pytest
from app import app

def test_hello():
    client = app.test_client()
    response = client.get('/api/hello')
    assert response.status_code == 200
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\test_app.py"
```

---

### Task DL-8: Add Environment Variables File
**File**: `daily\08-env-file.md`

### Task
Create `.env` in `python-api`:
```
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5000
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\.env"
```

---

## 📊 Data Analysis

### Task DL-9: Create a Data Summary
**File**: `daily\09-data-summary.md`

### Task
In `docs-site`, create `stats.md` that analyzes the other files:
- Count of `.md` files
- List of filenames
- Total lines across all markdown files

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\stats.md"
```

---

### Task DL-10: Generate a File Report
**File**: `daily\10-file-report.md`

### Task
Create `report.md` in `docs-site` listing all files in the `projects` folder:
- Folder name
- Number of files
- Key files

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\report.md"
```

---

## 🌐 Web & API

### Task DL-11: Create API Documentation
**File**: `daily\11-api-docs.md`

### Task
Create `API.md` in `python-api` documenting the `/api/hello` endpoint:
```markdown
# API Documentation

## GET /api/hello

Returns a greeting message.

### Response
```json
{
  "message": "Hello World"
}
```
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\API.md"
```

---

### Task DL-12: Create a Simple HTML Page
**File**: `daily\12-html-page.md`

### Task
Create `info.html` in `hello-world`:
```html
<!DOCTYPE html>
<html>
<head><title>Info</title></head>
<body>
  <h1>Project Info</h1>
  <p>Version: 1.0.0</p>
</body>
</html>
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\info.html"
```

---

## 📚 Learning & Notes

### Task DL-13: Create Study Notes
**File**: `daily\13-study-notes.md`

### Task
Create `learning.md` in `docs-site` with notes about JavaScript:
```markdown
# JavaScript Notes

## Variables
- let: block-scoped
- const: immutable
- var: function-scoped (avoid)

## Functions
- Arrow functions: () => {}
- Regular: function() {}
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\learning.md"
```

---

### Task DL-14: Create a Glossary
**File**: `daily\14-glossary.md`

### Task
Create `glossary.md` in `docs-site`:
```markdown
# Glossary

## API
Application Programming Interface

## SDK
Software Development Kit

## REST
Representational State Transfer
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\glossary.md"
```

---

## 🛠️ DevOps

### Task DL-15: Create Docker Config
**File**: `daily\15-dockerfile.md`

### Task
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

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\Dockerfile"
```

---

### Task DL-16: Create Docker Compose
**File**: `daily\16-compose.md`

### Task
Create `docker-compose.yml` in `python-api`:
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\python-api\docker-compose.yml"
```

---

## 📋 Project Management

### Task DL-17: Create Sprint Document
**File**: `daily\17-sprint.md`

### Task
Create `sprint-01.md` in `docs-site`:
```markdown
# Sprint 01

## Goals
- Set up project structure
- Implement core features

## Tasks
- [x] Create repo
- [ ] Setup CI/CD
- [ ] Implement feature A

## Timeline
- Start: 2026-05-04
- End: 2026-05-18
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\sprint-01.md"
```

---

### Task DL-18: Create Risk Log
**File**: `daily\18-risk-log.md`

### Task
Create `risks.md` in `docs-site`:
```markdown
# Risk Log

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Budget overrun | High | Medium | Monitor weekly |
| Timeline delay | Medium | High | Add buffer |
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\risks.md"
```

---

## 🔍 Search & Analysis

### Task DL-19: Find Large Files
**File**: `daily\19-large-files.md`

### Task
Search for the 3 largest files in `projects` folder and list them with sizes.

### Verification
Manual check - should identify the 3 largest files.

---

### Task DL-20: Find Recently Modified
**File**: `daily\20-recent-files.md`

### Task
List all files modified in the last 24 hours in the `projects` folder.

### Verification
```powershell
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\projects" -Recurse | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) }
```

---

## 🎨 Content Creation

### Task DL-21: Write a Product Description
**File**: `daily\21-product-desc.md`

### Task
Create `product.md` in `docs-site` describing the hello-world project:
- What it does
- Who it's for
- Key features
- Getting started

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\product.md"
```

---

### Task DL-22: Create an FAQ
**File**: `daily\22-faq.md`

### Task
Create `FAQ.md` in `docs-site`:
```markdown
# Frequently Asked Questions

## How do I install?
npm install

## How do I run?
npm start

## Is it free?
Yes, MIT license.
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\docs-site\FAQ.md"
```

---

## 🔐 Security

### Task DL-23: Create .gitignore
**File**: `daily\23-gitignore.md`

### Task
Create `.gitignore` in `hello-world`:
```
node_modules/
.env
dist/
*.log
.DS_Store
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\.gitignore"
```

---

### Task DL-24: Create Security Policy
**File**: `daily\24-security-policy.md`

### Task
Create `SECURITY.md` in `hello-world`:
```markdown
# Security Policy

## Supported Versions
| Version | Supported |
| ------- | -------- |
| 1.0.x   | ✅ |
| 0.9.x   | ❌ |

## Reporting a Vulnerability
Email: security@example.com
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\SECURITY.md"
```

---

## 📱 Automation

### Task DL-25: Create a Cron Script
**File**: `daily\25-cron.md`

### Task
Create `cron.sh` in `hello-world`:
```bash
#!/bin/bash
# Daily backup script
DATE=$(date +%Y-%m-%d)
echo "Running backup for $DATE"
```

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\cron.sh"
```

---

## How to Use

1. Select a task that matches your use case
2. Copy the Task section content
3. Paste into Cato-Claude agent
4. Verify using the PowerShell command
5. Check output matches Expected Result