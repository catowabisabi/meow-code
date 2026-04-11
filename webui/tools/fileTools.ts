/**
 * File operation tools — read, write, edit, search.
 */
import * as fs from 'fs'
import * as path from 'path'
import type { ToolDef, ToolContext, ToolResult } from './types.js'

// ─── File Read ────────────────────────────────────────────────

export const fileReadTool: ToolDef = {
  name: 'file_read',
  description: 'Read the contents of a file. Supports text files up to 5MB. Returns content with line numbers.',
  inputSchema: {
    type: 'object',
    required: ['file_path'],
    properties: {
      file_path: { type: 'string', description: 'Absolute path to the file' },
      offset: { type: 'number', description: 'Start line number (1-based)' },
      limit: { type: 'number', description: 'Max lines to read' },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const filePath = input.file_path as string
      if (!fs.existsSync(filePath)) {
        return { output: `File not found: ${filePath}`, isError: true }
      }
      const stat = fs.statSync(filePath)
      if (stat.size > 5 * 1024 * 1024) {
        return { output: 'File too large (max 5MB). Use offset/limit for partial reads.', isError: true }
      }

      const content = fs.readFileSync(filePath, 'utf-8')
      const lines = content.split('\n')
      const offset = (input.offset as number) || 1
      const limit = (input.limit as number) || lines.length
      const selected = lines.slice(offset - 1, offset - 1 + limit)
      const numbered = selected.map((line, i) => `${offset + i}\t${line}`).join('\n')

      return {
        output: numbered,
        isError: false,
        metadata: { totalLines: lines.length, size: stat.size },
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── File Write ───────────────────────────────────────────────

export const fileWriteTool: ToolDef = {
  name: 'file_write',
  description: 'Write content to a file. Creates parent directories if needed. Overwrites existing files.',
  inputSchema: {
    type: 'object',
    required: ['file_path', 'content'],
    properties: {
      file_path: { type: 'string', description: 'Absolute path to write to' },
      content: { type: 'string', description: 'Content to write' },
    },
  },
  isReadOnly: false,
  riskLevel: 'medium',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const filePath = input.file_path as string
      const content = input.content as string
      const dir = path.dirname(filePath)
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true })
      }
      fs.writeFileSync(filePath, content, 'utf-8')
      const lines = content.split('\n').length
      return {
        output: `Successfully wrote ${lines} lines to ${filePath}`,
        isError: false,
        metadata: { lines, bytes: Buffer.byteLength(content) },
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── File Edit (string replace) ──────────────────────────────

export const fileEditTool: ToolDef = {
  name: 'file_edit',
  description: 'Edit a file by replacing an exact string match. The old_string must appear exactly once in the file (or use replace_all for all occurrences).',
  inputSchema: {
    type: 'object',
    required: ['file_path', 'old_string', 'new_string'],
    properties: {
      file_path: { type: 'string', description: 'Absolute path to the file' },
      old_string: { type: 'string', description: 'Exact text to replace' },
      new_string: { type: 'string', description: 'Replacement text' },
      replace_all: { type: 'boolean', description: 'Replace all occurrences (default: false)' },
    },
  },
  isReadOnly: false,
  riskLevel: 'medium',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const filePath = input.file_path as string
      const oldStr = input.old_string as string
      const newStr = input.new_string as string
      const replaceAll = input.replace_all as boolean

      if (!fs.existsSync(filePath)) {
        return { output: `File not found: ${filePath}`, isError: true }
      }

      let content = fs.readFileSync(filePath, 'utf-8')
      const count = content.split(oldStr).length - 1

      if (count === 0) {
        return { output: `old_string not found in file. Make sure it matches exactly.`, isError: true }
      }
      if (count > 1 && !replaceAll) {
        return {
          output: `old_string found ${count} times. Set replace_all: true to replace all, or provide more context to make it unique.`,
          isError: true,
        }
      }

      if (replaceAll) {
        content = content.split(oldStr).join(newStr)
      } else {
        content = content.replace(oldStr, newStr)
      }

      fs.writeFileSync(filePath, content, 'utf-8')
      return {
        output: `Replaced ${replaceAll ? count + ' occurrences' : '1 occurrence'} in ${filePath}`,
        isError: false,
        metadata: { replacements: replaceAll ? count : 1 },
      }
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Glob (file search by pattern) ───────────────────────────

export const globTool: ToolDef = {
  name: 'glob',
  description: 'Find files by glob pattern (e.g. "**/*.ts", "src/**/*.tsx"). Returns matching file paths sorted by modification time.',
  inputSchema: {
    type: 'object',
    required: ['pattern'],
    properties: {
      pattern: { type: 'string', description: 'Glob pattern to match' },
      path: { type: 'string', description: 'Directory to search in (default: cwd)' },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const pattern = input.pattern as string
      const searchPath = (input.path as string) || ctx.cwd

      // Use shell glob via find/Get-ChildItem
      const isWin = process.platform === 'win32'
      const cmd = isWin
        ? `powershell -NoProfile -Command "Get-ChildItem -Path '${searchPath}' -Recurse -Name -Include '${pattern}' | Select-Object -First 200"`
        : `find '${searchPath}' -name '${pattern}' -type f 2>/dev/null | head -200`

      const { spawn: spawnSync } = await import('child_process')
      return new Promise((resolve) => {
        const proc = spawnSync(isWin ? 'powershell.exe' : '/bin/bash', isWin
          ? ['-NoProfile', '-Command', `Get-ChildItem -Path '${searchPath}' -Recurse -Name -Include '${pattern}' | Select-Object -First 200`]
          : ['-c', `find '${searchPath}' -name '${pattern}' -type f 2>/dev/null | head -200`], {
          cwd: searchPath,
          stdio: ['pipe', 'pipe', 'pipe'],
        })
        let out = ''
        proc.stdout?.on('data', (d: Buffer) => { out += d.toString() })
        proc.on('close', () => {
          const files = out.trim().split('\n').filter(Boolean)
          resolve({
            output: files.length > 0 ? files.join('\n') : 'No files found.',
            isError: false,
            metadata: { count: files.length },
          })
        })
        proc.on('error', (e) => resolve({ output: `Error: ${e.message}`, isError: true }))
      })
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}

// ─── Grep (content search) ───────────────────────────────────

export const grepTool: ToolDef = {
  name: 'grep',
  description: 'Search file contents using regex patterns. Returns matching lines with file paths and line numbers.',
  inputSchema: {
    type: 'object',
    required: ['pattern'],
    properties: {
      pattern: { type: 'string', description: 'Regex pattern to search for' },
      path: { type: 'string', description: 'File or directory to search in (default: cwd)' },
      include: { type: 'string', description: 'File glob to filter (e.g. "*.ts")' },
    },
  },
  isReadOnly: true,
  riskLevel: 'low',
  async execute(input, ctx): Promise<ToolResult> {
    try {
      const pattern = input.pattern as string
      const searchPath = (input.path as string) || ctx.cwd
      const include = input.include as string | undefined

      const isWin = process.platform === 'win32'
      let cmd: string

      if (isWin) {
        const includeArg = include ? `-Include '${include}'` : ''
        cmd = `Get-ChildItem -Path '${searchPath}' -Recurse ${includeArg} -File | Select-String -Pattern '${pattern}' | Select-Object -First 100 | ForEach-Object { "$($_.Path):$($_.LineNumber):$($_.Line)" }`
      } else {
        const includeArg = include ? `--include='${include}'` : ''
        cmd = `grep -rn ${includeArg} '${pattern}' '${searchPath}' 2>/dev/null | head -100`
      }

      const { spawn: spawnSync } = await import('child_process')
      return new Promise((resolve) => {
        const proc = spawnSync(isWin ? 'powershell.exe' : '/bin/bash',
          isWin ? ['-NoProfile', '-Command', cmd] : ['-c', cmd], {
          cwd: ctx.cwd,
          stdio: ['pipe', 'pipe', 'pipe'],
        })
        let out = ''
        proc.stdout?.on('data', (d: Buffer) => { out += d.toString() })
        proc.on('close', () => {
          const lines = out.trim().split('\n').filter(Boolean)
          resolve({
            output: lines.length > 0 ? lines.join('\n') : 'No matches found.',
            isError: false,
            metadata: { matchCount: lines.length },
          })
        })
        proc.on('error', (e) => resolve({ output: `Error: ${e.message}`, isError: true }))
      })
    } catch (err: unknown) {
      return { output: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true }
    }
  },
}
