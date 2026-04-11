#!/usr/bin/env python3
"""
Generate report.md from test_results.json
"""

import json
from datetime import datetime

with open("test_results.json", "r") as f:
    data = json.load(f)

results = data["results"]

template = """# API Server Test Report

## Summary

| Metric | Value |
|--------|-------|
| **Total Endpoints** | {total} |
| **Passed** | {passed} |
| **Failed** | {failed} |
| **Pass Rate** | {pass_rate} |

## Test Environment

- **API Server**: http://localhost:7778
- **Python Version**: 3.13.9
- **Framework**: FastAPI + Uvicorn
- **Test Date**: {test_date}

---

## Detailed Results

| # | Method | Endpoint | Status | Duration (ms) | Error |
|---|--------|----------|--------|---------------|-------|
"""

for i, r in enumerate(results):
    error = r.get("error", "")
    error_str = f"❌ {error[:50]}..." if error and not r["success"] else ""
    status_icon = "✅" if r["success"] else "❌"
    template += f"| {i+1} | {r['method']} | {r['name']} | {status_icon} {r['status']} | {r['duration_ms']} | {error_str} |\n"

failed_results = [r for r in results if not r["success"]]

template += f"""

## Failed Endpoints ({len(failed_results)})

"""

if failed_results:
    for r in failed_results:
        template += f"""### ❌ {r['name']}
- **Method**: {r['method']}
- **Path**: {r['path']}
- **Status**: {r['status']}
- **Error**: {r.get('error', 'N/A')}

"""
else:
    template += "All endpoints passed! 🎉\n"

durations = [r["duration_ms"] for r in results]
avg_duration = sum(durations) / len(durations) if durations else 0
fastest = min(durations) if durations else 0
slowest = max(durations) if durations else 0

template += f"""## Performance Metrics

| Metric | Value |
|--------|-------|
| **Average Response Time** | {avg_duration:.2f} ms |
| **Fastest Endpoint** | {fastest:.2f} ms |
| **Slowest Endpoint** | {slowest:.2f} ms |

---

## Code Quality Issues Found

During the porting and testing, the following issues were fixed:

1. **speculation.py**: `asyncio.AbortController` doesn't exist in Python 3.13 → imported from local `execution.py`
2. **loader.py**: `re.multiline` → `re.MULTILINE` (correct constant name)
3. **agent_pool.py**: `["string"].join()` → `"\n".join()` (correct syntax)
4. **privacy_settings.py**: Missing `log_event` → added stub function
5. **skills.py**: `from services.skills` → `from api_server.services.skills` (correct import path)
6. **hooks.py**: `command: str` with `command=None` → `command: Optional[str] = None` (type mismatch)
7. **register.py**: Removed non-existent `CONFIG_READ_TOOL`, `CONFIG_WRITE_TOOL` imports
8. **config.py**: Server runs on port 7778 (not 8000 as test_api.py assumed)

---

## Recommendations

### P0 (Critical)
1. Fix remaining import errors in tools/skill_tool.py (missing registry module)
2. Add authentication middleware to all `/api/*` routes
3. Fix session locking for concurrent access

### P1 (High)
4. Complete MCP transport types implementation
5. Add proper input validation with Pydantic
6. Implement memory search functionality

### P2 (Medium)
7. Add rate limiting middleware
8. Standardize error response format
9. Implement analytics events properly

### P3 (Low)
10. Add automatic session backup
11. Create comprehensive integration tests
12. Document all API endpoints with OpenAPI/Swagger

---

## GitHub Repository

Repository: `meow-code` (to be created)

To create the repository and push code:
```bash
# Install gh CLI if needed
winget install --id GitHub.cli -e

# Authenticate
gh auth login

# Create and push
cd api_server
gh repo create meow-code --public --source . --push
```

Or use the generated `create_repo.sh` script.
"""

with open("report.md", "w") as f:
    f.write(template.format(
        total=data["total"],
        passed=data["passed"],
        failed=data["failed"],
        pass_rate=data["pass_rate"],
        test_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

print(f"Report generated: report.md")
print(f"Summary: {data['passed']}/{data['total']} passed ({data['pass_rate']})")
