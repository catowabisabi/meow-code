"""
Command semantics configuration for interpreting exit codes in PowerShell.

PowerShell-native cmdlets do NOT need exit-code semantics:
- Select-String (grep equivalent) exits 0 on no-match (returns $null)
- Compare-Object (diff equivalent) exits 0 regardless
- Test-Path exits 0 regardless (returns bool via pipeline)

External executables invoked from PowerShell DO set $LASTEXITCODE,
and many use non-zero codes to convey information rather than failure.
"""

from typing import Callable

CommandSemantic = Callable[[int, str, str], tuple]


def default_semantic(exit_code: int, _stdout: str, _stderr: str) -> tuple:
    is_error = exit_code != 0
    message = f'Command failed with exit code {exit_code}' if is_error else None
    return (is_error, message)


def grep_semantic(exit_code: int, _stdout: str, _stderr: str) -> tuple:
    is_error = exit_code >= 2
    message = 'No matches found' if exit_code == 1 else None
    return (is_error, message)


def robocopy_semantic(exit_code: int, _stdout: str, _stderr: str) -> tuple:
    if exit_code >= 8:
        return (True, f'Robocopy failed with exit code {exit_code}')
    
    messages = {
        0: 'No files copied (already in sync)',
        1: 'Files copied successfully',
        2: 'Extra files/dirs detected (no copy)',
        4: 'Mismatched files/dirs detected',
    }
    
    message = messages.get(exit_code, f'Robocopy completed with exit code {exit_code}')
    return (False, message)


COMMAND_SEMANTICS = {
    'grep': grep_semantic,
    'rg': grep_semantic,
    'findstr': grep_semantic,
    'robocopy': robocopy_semantic,
}


def extract_base_command(segment: str) -> str:
    stripped = segment.strip()
    if stripped.startswith('& ') or stripped.startswith('.'):
        parts = stripped.split()
        if len(parts) > 1:
            stripped = ' '.join(parts[1:])
    
    first_token = stripped.split()[0] if stripped.split() else ''
    unquoted = first_token.strip('"\'')
    
    basename = unquoted.split('/')[-1].split('\\')[-1]
    return basename.lower().replace('.exe', '')


def heuristically_extract_base_command(command: str) -> str:
    segments = [s.strip() for s in command.split(';') if s.strip()]
    segments += [s.strip() for s in command.split('|') if s.strip()]
    
    if not segments:
        return ''
    
    return extract_base_command(segments[-1])


def interpret_command_result(command: str, exit_code: int, stdout: str, stderr: str) -> dict:
    base_command = heuristically_extract_base_command(command)
    semantic = COMMAND_SEMANTICS.get(base_command, default_semantic)
    is_error, message = semantic(exit_code, stdout, stderr)
    return {'isError': is_error, 'message': message}