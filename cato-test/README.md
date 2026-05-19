# Cato-Claude Test Suite

## Location
`C:\Users\enoma\Desktop\cato-test`

## Test Projects
- **hello-world** - Simple Node.js project
- **python-api** - Python Flask API
- **react-app** - React + Vite project
- **docs-site** - Markdown documentation site

---

## Test Scripts (45 tests total)

### Standard API Tests (20 tests)
**Folder**: `test-scripts/`

| # | Category | Description | File |
|---|----------|-------------|------|
| 01 | File | Create a file with content | 01-file-creation.md |
| 02 | File | Create nested folder structure | 02-nested-folders.md |
| 03 | Analysis | Read and parse package.json | 03-read-package-json.md |
| 04 | Analysis | Analyze project structure | 04-structure-analysis.md |
| 05 | Git | Git init | 05-git-init.md |
| 06 | Git | Git status | 06-git-status.md |
| 07 | Search | Search for keyword | 07-search-function.md |
| 08 | Search | Count lines of code | 08-loc-count.md |
| 09 | Analysis | Find entry point | 09-find-entry.md |
| 10 | Modify | Search and replace | 10-search-replace.md |
| 11 | File | Delete a file | 11-delete-file.md |
| 12 | File | Batch create 3 files | 12-batch-create.md |
| 13 | Shell | Shell list files | 13-shell-list.md |
| 14 | File | Append to file | 14-append-content.md |
| 15 | Modify | Create Python file | 15-python-utils.md |
| 16 | Search | Multi-project search | 16-multi-file-search.md |
| 17 | Search | Search by file type (.jsx) | 17-search-jsx.md |
| 18 | File | Directory listing | 18-dir-listing.md |
| 19 | Analysis | Read multiple files | 19-read-multiple.md |
| 20 | Analysis | Verify file existence | 20-verify-exists.md |

### Daily Life Tasks (25 tests)
**Folder**: `test-scripts/daily/`

| # | Category | Description | File |
|---|----------|-------------|------|
| DL-01 | Writing | Write a Meeting Note | 01-meeting-notes.md |
| DL-02 | Writing | Update README | 02-update-readme.md |
| DL-03 | Writing | Create a Changelog | 03-changelog.md |
| DL-04 | Files | Sort Files by Type | 04-sort-files.md |
| DL-05 | DevOps | Create Backup Script | 05-backup-script.md |
| DL-06 | Dev | Add npm Script | 06-add-script.md |
| DL-07 | Dev | Create Python Test | 07-python-test.md |
| DL-08 | Dev | Add Environment File | 08-env-file.md |
| DL-09 | Data | Create Data Summary | 09-data-summary.md |
| DL-10 | Data | Generate File Report | 10-file-report.md |
| DL-11 | Web | Create API Documentation | 11-api-docs.md |
| DL-12 | Web | Create HTML Page | 12-html-page.md |
| DL-13 | Learning | Create Study Notes | 13-study-notes.md |
| DL-14 | Learning | Create a Glossary | 14-glossary.md |
| DL-15 | DevOps | Create Dockerfile | 15-dockerfile.md |
| DL-16 | DevOps | Create Docker Compose | 16-compose.md |
| DL-17 | PM | Create Sprint Document | 17-sprint.md |
| DL-18 | PM | Create Risk Log | 18-risk-log.md |
| DL-19 | Search | Find Large Files | 19-large-files.md |
| DL-20 | Search | Find Recently Modified | 20-recent-files.md |
| DL-21 | Content | Write Product Description | 21-product-desc.md |
| DL-22 | Content | Create an FAQ | 22-faq.md |
| DL-23 | Security | Create .gitignore | 23-gitignore.md |
| DL-24 | Security | Create Security Policy | 24-security-policy.md |
| DL-25 | Automation | Create Cron Script | 25-cron.md |

---

## How to Run

### Option 1: Manual Testing
1. Open Cato-Claude in **Code mode**
2. Set working folder: `C:\Users\enoma\Desktop\cato-test`
3. Choose a test from the lists above
4. Read the task from the `.md` file in `test-scripts/` or `test-scripts/daily/`
5. Paste the task into the agent
6. Run the verification command

### Option 2: Batch Testing
```powershell
# List all test files
Get-ChildItem "C:\Users\enoma\Desktop\cato-test\test-scripts" -Recurse -Filter "*.md"

# Run a specific test verification
Get-Content "C:\Users\enoma\Desktop\cato-test\test-scripts\01-file-creation.md"
```

---

## Verification

Each test has a PowerShell verification command at the bottom. Run it to confirm the test passed.

Example:
```powershell
# Test 1 verification
Get-Content "C:\Users\enoma\Desktop\cato-test\projects\hello-world\hello.txt"

# Test 5 verification (git init)
Test-Path "C:\Users\enoma\Desktop\cato-test\projects\hello-world\.git"
```

---

## Expected Duration

| Category | Time per Task |
|----------|---------------|
| File Operations | 10-30 seconds |
| Git Operations | 15-30 seconds |
| Search Operations | 20-60 seconds |
| Analysis Tasks | 30-90 seconds |
| Complex Tasks (Docker, etc.) | 1-3 minutes |

---

## Notes

- Most tests are independent and can run in any order
- Tests DL-01, DL-04 modify existing files - results accumulate
- Git tests (05-06) require sequential execution (init before status)
- Some tests create files that persist for subsequent tests