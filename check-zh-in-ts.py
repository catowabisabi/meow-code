#!/usr/bin/env python3
"""
Scan TypeScript files to find files with less than 100 Chinese characters.
Used to verify documentation annotation completeness.
"""

import os
import re
from pathlib import Path

# Pattern to match Chinese characters (CJK Unified Ideographs)
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')

def count_chinese_chars(content: str) -> int:
    """Count the number of Chinese characters in content."""
    return len(CHINESE_PATTERN.findall(content))

def scan_directory(base_path: str) -> list[tuple[str, int, str]]:
    """
    Scan all .ts and .tsx files in the directory.
    Returns list of (file_path, chinese_count, first_10_chars) tuples.
    """
    results = []
    base = Path(base_path)
    
    for file_path in base.rglob('*.ts'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            chinese_count = count_chinese_chars(content)
            first_10_zh = ''.join(CHINESE_PATTERN.findall(content)[:10])
            relative_path = str(file_path.relative_to(base))
            results.append((relative_path, chinese_count, first_10_zh))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    for file_path in base.rglob('*.tsx'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            chinese_count = count_chinese_chars(content)
            first_10_zh = ''.join(CHINESE_PATTERN.findall(content)[:10])
            relative_path = str(file_path.relative_to(base))
            results.append((relative_path, chinese_count, first_10_zh))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return results

def main():
    src_path = r"F:\codebase\cato-claude\_claude_code_leaked_source_code\src"
    
    print(f"Scanning directory: {src_path}")
    print("=" * 80)
    
    results = scan_directory(src_path)
    
    # Filter files with less than 100 Chinese characters
    missing_docs = [(path, count, zh) for path, count, zh in results if count < 100]
    
    # Sort by path
    missing_docs.sort(key=lambda x: x[0])
    
    print(f"\nTotal files scanned: {len(results)}")
    print(f"Files with < 10 Chinese characters: {len(missing_docs)}")
    print("=" * 80)
    
    # Output to file
    output_file = r"F:\codebase\cato-claude\check-zh-in-ts-output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Files with less than 10 Chinese characters in {src_path}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total files scanned: {len(results)}\n")
        f.write(f"Files with < 10 Chinese characters: {len(missing_docs)}\n")
        f.write("=" * 80 + "\n\n")
        
        for path, count, first_10 in missing_docs:
            f.write(f"{path}\n")
            f.write(f"  Chinese chars: {count}\n")
            if first_10:
                f.write(f"  First 10 Chinese chars: {first_10}\n")
            f.write("\n")
    
    print(f"\nOutput written to: {output_file}")
    
    # Also print to console
    print("\n" + "=" * 80)
    print("FILES WITH < 10 CHINESE CHARACTERS:")
    print("=" * 80)
    for path, count, first_10 in missing_docs:
        print(f"{path} (count: {count})")

if __name__ == '__main__':
    main()
