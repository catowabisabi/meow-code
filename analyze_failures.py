import json
with open('F:/codebase/cato-claude/api_server/test_results.json') as f:
    data = json.load(f)
print("=== FAILED ENDPOINTS ===")
for r in data['results']:
    if not r['success']:
        print(f"{r['method']} {r['path']} -> {r['status']}: {r['error']}")