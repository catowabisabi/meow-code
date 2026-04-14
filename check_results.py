import json
with open('F:/codebase/cato-claude/api_server/test_results_v2.json') as f:
    data = json.load(f)
print(f"Total: {data['total']}, Passed: {data['passed']}, Failed: {data['failed']}, Rate: {data['pass_rate']}")
print("\nFailed endpoints:")
for r in data['results']:
    if not r['success']:
        print(f"  {r['method']} {r['path']} -> {r['status']}: {r['error']}")