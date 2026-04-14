from pathlib import Path
try:
    content = Path('F:/codebase/cato-claude/README.md').read_text(encoding='utf-8')
    print(f"Successfully read {len(content)} chars")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")