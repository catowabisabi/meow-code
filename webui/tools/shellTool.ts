/**
 * Shell execution tool — runs Bash/PowerShell/cmd commands.
 * This is the most powerful tool: direct OS command execution.
 */
import { spawn } from 'child_process'
import * as os from 'os'
import type { ToolDef, ToolContext, ToolResult, ToolProgress } from './types.js'

const isWindows = os.platform() === 'win32'

interface ShellInput {
  command: string
  timeout?: number
  shell?: 'bash' | 'powershell' | 'cmd' | 'auto'
  cwd?: string
}

function getShell(preference?: string): { cmd: string; args: string[] } {
  if (preference === 'powershell') {
    return { cmd: 'powershell.exe', args: ['-NoProfile', '-Command'] }
  }
  if (preference === 'bash') {
    return { cmd: isWindows ? 'bash.exe' : '/bin/bash', args: ['-c'] }
  }
  if (preference === 'cmd') {
    return { cmd: 'cmd.exe', args: ['/c'] }
  }
  // auto: Windows defaults to PowerShell, others to bash
  if (isWindows) {
    return { cmd: 'powershell.exe', args: ['-NoProfile', '-Command'] }
  }
  return { cmd: '/bin/bash', args: ['-c'] }
}

export function executeShellCommand(
  input: ShellInput,
  ctx: ToolContext,
): Promise<ToolResult> {
  return new Promise((resolve) => {
    const { cmd, args } = getShell(input.shell)
    const timeout = input.timeout || 120000 // 2 minutes default
    const cwd = input.cwd || ctx.cwd

    let stdout = ''
    let stderr = ''
    let killed = false

    const proc = spawn(cmd, [...args, input.command], {
      cwd,
      env: { ...process.env },
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    })

    // Timeout handler
    const timer = setTimeout(() => {
      killed = true
      proc.kill('SIGTERM')
      setTimeout(() => proc.kill('SIGKILL'), 5000)
    }, timeout)

    // Stream stdout
    proc.stdout?.on('data', (chunk: Buffer) => {
      const text = chunk.toString()
      stdout += text
      ctx.onProgress?.({
        toolName: 'shell',
        toolId: '',
        type: 'stdout',
        data: text,
      })
    })

    // Stream stderr
    proc.stderr?.on('data', (chunk: Buffer) => {
      const text = chunk.toString()
      stderr += text
      ctx.onProgress?.({
        toolName: 'shell',
        toolId: '',
        type: 'stderr',
        data: text,
      })
    })

    // Abort signal
    if (ctx.abortSignal) {
      ctx.abortSignal.addEventListener('abort', () => {
        killed = true
        proc.kill('SIGTERM')
      })
    }

    proc.on('close', (code) => {
      clearTimeout(timer)

      // Truncate large output
      const maxLen = 50000
      let output = stdout
      if (output.length > maxLen) {
        output = output.slice(0, maxLen) + `\n... (truncated, ${stdout.length} total chars)`
      }

      if (stderr) {
        output += (output ? '\n' : '') + `[stderr]\n${stderr.slice(0, 10000)}`
      }

      if (killed) {
        output += '\n[Process terminated: timeout or abort]'
      }

      resolve({
        output: output || '(no output)',
        isError: code !== 0,
        metadata: { exitCode: code, killed },
      })
    })

    proc.on('error', (err) => {
      clearTimeout(timer)
      resolve({
        output: `Failed to execute command: ${err.message}`,
        isError: true,
      })
    })
  })
}

export const shellTool: ToolDef = {
  name: 'shell',
  description: `Execute shell commands on the user's computer. On Windows, defaults to PowerShell; on Linux/Mac, defaults to Bash. Use this for: running scripts, installing packages, git operations, file manipulation, running tests, builds, etc.`,
  inputSchema: {
    type: 'object',
    required: ['command'],
    properties: {
      command: {
        type: 'string',
        description: 'The shell command to execute',
      },
      timeout: {
        type: 'number',
        description: 'Timeout in milliseconds (default: 120000)',
      },
      shell: {
        type: 'string',
        enum: ['bash', 'powershell', 'cmd', 'auto'],
        description: 'Shell to use (default: auto)',
      },
      cwd: {
        type: 'string',
        description: 'Working directory (default: server cwd)',
      },
    },
  },
  isReadOnly: false,
  riskLevel: 'high',
  execute: (input, ctx) => executeShellCommand(input as unknown as ShellInput, ctx),
}
