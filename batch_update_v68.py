#!/usr/bin/env python3
"""Batch update v68 - Analyze ExitPlanModeTool remaining files and more tools"""

import sqlite3
import os
import re
from datetime import datetime

CLAUDE_SRC = r"F:\codebase\cato-claude\_claude_code_leaked_source_code\src"
DB_PATH = r"F:\codebase\cato-claude\progress.db"

# Files to analyze in this batch
BATCH_FILES = [
    r"src\tools\ExitPlanModeTool\ExitPlanModeTool.ts",
    r"src\tools\ExitPlanModeTool\prompt.ts",
    r"src\tools\ExitPlanModeTool\types.ts",
    r"src\tools\FetchRemoteBranchTool\constants.ts",
    r"src\tools\FetchRemoteBranchTool\FetchRemoteBranchTool.ts",
    r"src\tools\FetchRemoteBranchTool\prompt.ts",
    r"src\tools\GrepTool\GrepTool.ts",
    r"src\tools\GrepTool\constants.ts",
    r"src\tools\GrepTool\prompt.ts",
    r"src\tools\GrepTool\types.ts",
]

def analyze_file(src_path):
    """Analyze a single TypeScript file and generate summary"""
    full_path = os.path.join(CLAUDE_SRC, src_path)
    
    if not os.path.exists(full_path):
        return None, "FILE_NOT_FOUND"
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Extract imports
        imports = []
        for line in lines[:30]:
            match = re.match(r"^import\s+.*?from\s+['\"](.+?)['\"]", line)
            if match:
                imports.append(match.group(1))
        
        # Extract exports (functions, classes, interfaces)
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
        
        # Detect category based on path
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
        
        # Generate summary
        summary = f"[{category.upper()}] {len(lines)} lines, {len(exports)} exports"
        if imports:
            summary += f", imports: {', '.join(imports[:3])}"
        
        return summary, "analyzed"
        
    except Exception as e:
        return f"ERROR: {str(e)}", "error"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    updated = 0
    for src_path in BATCH_FILES:
        db_path = src_path.replace('\\', '\\\\')
        
        # Check if exists
        c.execute('SELECT id FROM files WHERE src_path=?', (db_path,))
        row = c.fetchone()
        
        if row:
            summary, status = analyze_file(src_path)
            if summary:
                c.execute('''
                    UPDATE files 
                    SET summary=?, status=?, analyzed_at=?, notes=NULL
                    WHERE src_path=?
                ''', (summary, status, datetime.now().isoformat(), db_path))
                updated += 1
                print(f"[+] {src_path}")
        else:
            print(f"[-] Not in DB: {src_path}")
    
    conn.commit()
    conn.close()
    print(f"\nTotal records updated: {updated}")

if __name__ == "__main__":
    main()
