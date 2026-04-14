#!/usr/bin/env python3
"""Batch update v70 - Analyze pending files"""

import sqlite3
import os
import re
from datetime import datetime

CLAUDE_SRC = r"F:\codebase\cato-claude\_claude_code_leaked_source_code\src"
DB_PATH = r"F:\codebase\cato-claude\progress.db"

def analyze_file(src_path):
    full_path = os.path.join(CLAUDE_SRC, src_path)
    
    if not os.path.exists(full_path):
        return None, "FILE_NOT_FOUND"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        imports = []
        for line in lines[:30]:
            match = re.match(r"^import\s+.*?from\s+['\"](.+?)['\"]", line)
            if match:
                imports.append(match.group(1))
        
        exports = []
        for line in lines:
            func_match = re.match(r"^export\s+(?:async\s+)?function\s+(\w+)", line)
            if func_match:
                exports.append(f"function:{func_match.group(1)}")
            class_match = re.match(r"^export\s+(?:abstract\s+)?class\s+(\w+)", line)
            if class_match:
                exports.append(f"class:{class_match.group(1)}")
            interface_match = re.match(r"^export\s+interface\s+(\w+)", line)
            if interface_match:
                exports.append(f"interface:{interface_match.group(1)}")
        
        if '\\tools\\' in src_path:
            category = "tools"
        elif '\\commands\\' in src_path:
            category = "commands"
        elif '\\cli\\' in src_path:
            category = "cli"
        elif '\\utils\\' in src_path:
            category = "utils"
        elif '\\hooks\\' in src_path:
            category = "hooks"
        elif '\\lib\\' in src_path:
            category = "lib"
        elif '\\branches\\' in src_path:
            category = "branches"
        elif '\\api\\' in src_path:
            category = "api"
        elif '\\services\\' in src_path:
            category = "services"
        elif '\\bridge\\' in src_path:
            category = "bridge"
        elif '\\bootstrap\\' in src_path:
            category = "bootstrap"
        else:
            category = "other"
        
        summary = f"[{category.upper()}] {len(lines)} lines, {len(exports)} exports"
        if imports:
            summary += f", imports: {', '.join(imports[:3])}"
        
        return summary, "analyzed"
        
    except Exception as e:
        return f"ERROR: {str(e)}", "error"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT src_path FROM files WHERE status=? LIMIT 30', ('pending',))
    pending_files = [row[0] for row in c.fetchall()]
    
    print(f"Processing {len(pending_files)} pending files...")
    
    updated = 0
    for src_path in pending_files:
        summary, status = analyze_file(src_path)
        if summary:
            c.execute('''
                UPDATE files 
                SET summary=?, status=?, analyzed_at=?
                WHERE src_path=?
            ''', (summary, status, datetime.now().isoformat(), src_path))
            updated += 1
            print(f"[+] {src_path}")
    
    conn.commit()
    conn.close()
    print(f"\nTotal records updated: {updated}")

if __name__ == "__main__":
    main()
