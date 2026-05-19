# Cato-Claude API Test Suite

## Overview
These test scripts verify the Cato-Claude agent's ability to perform various tasks in the test project folder.

**Test Folder**: `C:\Users\enoma\Desktop\cato-test`

---

## Test 1: File Creation
**File**: `01-file-creation.md`

### Task
Create a new file called `hello.txt` in the `hello-world` project folder with the exact content:
```
Hello World
This is a test file.
```

### Expected Result
- File exists at `C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt`
- Content matches exactly

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"
```

---

## Test 2: Nested Folder Creation
**File**: `02-nested-folders.md`

### Task
Create a nested folder structure `a/b/c/d.txt` in the `docs-site` project. The file `d.txt` should contain:
```
Deep nested file
```

### Expected Result
- Folder structure: `docs-site/a/b/c/d.txt` exists

### Verification
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\docs-site\a\b\c\d.txt"
```

---

## Test 3: File Reading & Analysis
**File**: `03-read-package-json.md`

### Task
Read the `package.json` file in the `react-app` project and list all dependencies and devDependencies.

### Expected Result
- Shows: react, react-dom, @vitejs/plugin-react, vite
- Shows version numbers

### Verification
Check that the output mentions all 4 dependencies with versions.

---

## Test 4: Project Structure Analysis
**File**: `04-structure-analysis.md`

### Task
Analyze the structure of the `python-api` project and tell me:
1. What files exist?
2. What is the main entry point?
3. What dependencies are needed?

### Expected Result
- Lists: app.py, requirements.txt, README.md
- Identifies app.py as main
- Lists flask, flask-cors

---

## Test 5: Git Initialization
**File**: `05-git-init.md`

### Task
Initialize a git repository in the `hello-world` project folder.

### Expected Result
- `.git` folder exists

### Verification
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\.git"
```

---

## Test 6: Git Status
**File**: `06-git-status.md`

### Task
Run `git status` in the `hello-world` project and tell me what untracked files exist.

### Expected Result
- Lists: index.js, package.json, README.md as untracked

---

## Test 7: Code Search - Find Function
**File**: `07-search-function.md`

### Task
Search for all files in `python-api/` that contain the word "Flask" (case-insensitive).

### Expected Result
- Finds: app.py contains "Flask"

---

## Test 8: Count Lines of Code
**File**: `08-loc-count.md`

### Task
Count the total lines of code in the `react-app/src` folder.

### Expected Result
- Should return a number > 10 (we have main.jsx and App.jsx)

### Verification
```powershell
(Get-ChildItem -Path "C:\Users\enoma\Desktop\cato-test\projects\react-app\src" -Recurse -File | Get-Content | Measure-Object -Line).Lines
```

---

## Test 9: Find Entry Point
**File**: `09-find-entry.md`

### Task
Find the main entry point file in the `react-app` project (look for index.html or main.jsx).

### Expected Result
- Identifies: src/main.jsx as the JS entry

---

## Test 10: Search and Replace
**File**: `10-search-replace.md`

### Task
In the `docs-site` project, find all `.md` files and replace the text "TODO" with "TASKS" in each file.

### Expected Result
- Files are modified, TODO → TASKS

### Verification
```powershell
Select-String -Path "C:\Users\enoma\Desktop\cato-test\projects\docs-site\*.md" -Pattern "TASKS"
```

---

## Test 11: File Deletion
**File**: `11-delete-file.md`

### Task
Delete the file `hello.txt` in `hello-world` that we created in Test 1.

### Expected Result
- File no longer exists

### Verification
```powershell
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"  # Should be False
```

---

## Test 12: Batch File Creation
**File**: `12-batch-create.md`

### Task
Create 3 new files in `docs-site`:
- `info.txt` with "Project info"
- `version.txt` with "Version: 1.0.0"
- `status.txt` with "Status: Active"

### Expected Result
- All 3 files exist with correct content

---

## Test 13: Shell Command - List Files
**File**: `13-shell-list.md`

### Task
Run a shell command to list all files (excluding hidden) in the `projects` folder.

### Expected Result
- Lists all project folders

---

## Test 14: Append to File
**File**: `14-append-content.md`

### Task
Append the following text to `README.md` in `hello-world`:
```
Last updated: 2026-05-04
```

### Expected Result
- Original content + new line preserved

### Verification
```powershell
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\README.md"
```

---

## Test 15: Create Python File
**File**: `15-python-utils.md`

### Task
Create a new file `utils.py` in `python-api` with this content:
```python
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
```

### Expected Result
- File exists with both functions

---

## Test 16: Multi-File Search
**File**: `16-multi-file-search.md`

### Task
Search all projects for files that contain the word "Hello" (case-insensitive).

### Expected Result
- hello-world/index.js
- react-app/src/App.jsx
- docs-site/README.md

---

## Test 17: File Type Search
**File**: `17-search-jsx.md`

### Task
Find all `.jsx` files in the `react-app` project.

### Expected Result
- src/main.jsx
- src/App.jsx

---

## Test 18: Directory Listing
**File**: `18-dir-listing.md`

### Task
List all directories in `projects/`.

### Expected Result
- hello-world
- python-api
- react-app
- docs-site

---

## Test 19: Read Multiple Files
**File**: `19-read-multiple.md`

### Task
Read both `app.py` and `requirements.txt` from `python-api` and summarize what the project does.

### Expected Result
- Identifies it as Flask API
- Lists dependencies

---

## Test 20: Verify File Exists
**File**: `20-verify-exists.md`

### Task
Check if these files exist:
1. `hello-world/package.json`
2. `python-api/app.py`
3. `react-app/package.json`
4. `docs-site/README.md`

Report which exist and which don't.

### Expected Result
- All 4 files should exist

---

## How to Run Tests

1. Open Cato-Claude in Code mode with folder: `C:\Users\enoma\Desktop\cato-test`
2. Copy the task description from the desired test
3. Paste to the agent
4. Compare the agent's response with the expected result
5. Run the verification command to confirm