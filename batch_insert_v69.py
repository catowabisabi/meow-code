#!/usr/bin/env python3
"""Batch insert v69 - Insert missing tools files into database"""

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
    
    # Get all files already in DB
    c.execute('SELECT src_path FROM files')
    db_files = set(row[0] for row in c.fetchall())
    
    # Find all tools files in source
    tools_src = os.path.join(CLAUDE_SRC, 'tools')
    to_insert = []
    
    if os.path.exists(tools_src):
        for root, dirs, files in os.walk(tools_src):
            for f in files:
                if f.endswith('.ts') or f.endswith('.tsx'):
                    src_path = os.path.join(root, f).replace(CLAUDE_SRC, 'src').replace('/', '\\')
                    if src_path not in db_files:
                        to_insert.append(src_path)
    
    print(f"Found {len(to_insert)} files to insert")
    
    inserted = 0
    for src_path in to_insert:
        summary, status = analyze_file(src_path)
        if summary:
            c.execute('''
                INSERT OR IGNORE INTO files (src_path, category, summary, status, analyzed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (src_path, status.split()[0] if ' ' in status else status, summary, status, datetime.now().isoformat()))
            inserted += 1
            print(f"[+] {src_path}")
    
    conn.commit()
    conn.close()
    print(f"\nTotal records inserted: {inserted}")

if __name__ == "__main__":
    main()
