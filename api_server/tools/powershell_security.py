"""
PowerShell-specific security analysis for command validation.

Detects dangerous patterns: code injection, download cradles, privilege
escalation, dynamic command names, COM objects, etc.
"""

import re
from typing import Optional

# PowerShell executables
POWERSHELL_EXECUTABLES = {'pwsh', 'pwsh.exe', 'powershell', 'powershell.exe'}

# Downloader names for download cradle detection
DOWNLOADER_NAMES = {
    'invoke-webrequest', 'iwr',
    'invoke-restmethod', 'irm',
    'new-object',
    'start-bitstransfer',
}

# Cmdlets where script blocks are safe (filtering/output cmdlets)
SAFE_SCRIPT_BLOCK_CMDLETS = {
    'where-object', 'sort-object', 'select-object', 'group-object',
    'format-table', 'format-list', 'format-wide', 'format-custom',
}

# Dangerous script block cmdlets
DANGEROUS_SCRIPT_BLOCK_CMDLETS = {
    'invoke-command', 'icm',
    'invoke-expression', 'iex',
    'start-job', 'sj',
    'start-threadjob',
    'register-scheduledjob',
    'foreach-object', 'foreach', '%',
}

# File path execution cmdlets
FILEPATH_EXECUTION_CMDLETS = {
    'invoke-command', 'icm',
    'start-job',
    'start-threadjob',
    'register-scheduledjob',
}

# Module loading cmdlets
MODULE_LOADING_CMDLETS = {
    'import-module', 'ipmo',
    'install-module',
    'save-module',
    'update-module',
    'install-packageprovider',
    'save-package',
}

# Environment variable write cmdlets
ENV_WRITE_CMDLETS = {
    'set-item', 'si',
    'new-item', 'ni',
    'remove-item', 'ri', 'del', 'rm', 'rd', 'rmdir', 'erase',
    'clear-item', 'cli',
    'set-content', 'sc',
    'add-content', 'ac',
}

# Runtime state manipulation cmdlets
RUNTIME_STATE_CMDLETS = {
    'set-alias', 'sal',
    'new-alias', 'nal',
    'set-variable', 'sv',
    'new-variable', 'nv',
}

# WMI spawn cmdlets
WMI_SPAWN_CMDLETS = {
    'invoke-wmimethod', 'iwmi',
    'invoke-cimmethod',
}

# Scheduled task cmdlets
SCHEDULED_TASK_CMDLETS = {
    'register-scheduledtask',
    'new-scheduledtask',
    'new-scheduledtaskaction',
    'set-scheduledtask',
}


def is_powershell_executable(name: str) -> bool:
    """Check if a name is a PowerShell executable."""
    lower = name.lower()
    if lower in POWERSHELL_EXECUTABLES:
        return True
    # Extract basename from paths
    last_sep = max(lower.rfind('/'), lower.rfind('\\'))
    if last_sep >= 0:
        return lower[last_sep + 1:] in POWERSHELL_EXECUTABLES
    return False


def _check_dangerous_param(cmd_args: list, param_patterns: list) -> bool:
    """Check if args contain dangerous parameter patterns."""
    for i, arg in enumerate(cmd_args):
        lower_arg = arg.lower()
        for pattern in param_patterns:
            if lower_arg == pattern or lower_arg.startswith(f'{pattern}:'):
                return True
            # Check next arg as value
            if i + 1 < len(cmd_args) and lower_arg == pattern:
                return True
    return False


def _extract_param_value(cmd_args: list, param_name: str) -> Optional[str]:
    """Extract value for a parameter from command args."""
    param_lower = param_name.lower()
    for i, arg in enumerate(cmd_args):
        arg_lower = arg.lower()
        if arg_lower == param_lower or arg_lower.startswith(f'{param_lower}:'):
            # Colon syntax
            if ':' in arg:
                return arg[arg.index(':') + 1:]
            # Next arg is value
            if i + 1 < len(cmd_args):
                return cmd_args[i + 1]
        if arg_lower.startswith(param_lower + ':') and len(arg_lower) > len(param_lower) + 1:
            return arg[arg_lower.index(':') + 1:]
    return None


def check_invoke_expression(command_parts: list, all_parts: list) -> tuple:
    """Check for Invoke-Expression usage."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower == 'invoke-expression' or name_lower == 'iex':
            return 'ask', 'Command uses Invoke-Expression which can execute arbitrary code'
    return 'passthrough', None


def check_dynamic_command_name(command_parts: list) -> tuple:
    """Check for dynamic command invocation."""
    for cmd in command_parts:
        name = cmd.get('name', '')
        name_type = cmd.get('nameType', '')
        # Only StringConstant is safe for command names
        if name_type != 'StringConstant' and name:
            return 'ask', 'Command name is a dynamic expression which cannot be statically validated'
    return 'passthrough', None


def check_encoded_command(command_parts: list) -> tuple:
    """Check for -EncodedCommand parameter."""
    for cmd in command_parts:
        if is_powershell_executable(cmd.get('name', '')):
            args = cmd.get('args', [])
            for i, arg in enumerate(args):
                arg_lower = arg.lower()
                if arg_lower in ('-encodedcommand', '-e') or arg_lower.startswith('-encodedcommand:') or arg_lower.startswith('-e:'):
                    return 'ask', 'Command uses encoded parameters which obscure intent'
                if arg_lower == '-encodedcommand' and i + 1 < len(args):
                    return 'ask', 'Command uses encoded parameters which obscure intent'
    return 'passthrough', None


def check_pwsh_command_or_file(command_parts: list) -> tuple:
    """Check for nested PowerShell process invocation."""
    for cmd in command_parts:
        if is_powershell_executable(cmd.get('name', '')):
            return 'ask', 'Command spawns a nested PowerShell process which cannot be validated'
    return 'passthrough', None


def check_download_cradles(command_parts: list) -> tuple:
    """Check for download cradle patterns (IWR | IEX)."""
    has_downloader = False
    has_iex = False
    
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower in DOWNLOADER_NAMES:
            has_downloader = True
        if name_lower == 'invoke-expression' or name_lower == 'iex':
            has_iex = True
    
    if has_downloader and has_iex:
        return 'ask', 'Command downloads and executes remote code'
    return 'passthrough', None


def check_download_utilities(command_parts: list) -> tuple:
    """Check for standalone download utilities."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        args = cmd.get('args', [])
        
        if name_lower == 'start-bitstransfer':
            return 'ask', 'Command downloads files via BITS transfer'
        
        if name_lower == 'certutil' or name_lower == 'certutil.exe':
            for arg in args:
                if arg.lower() in ('-urlcache', '/urlcache'):
                    return 'ask', 'Command uses certutil to download from a URL'
        
        if name_lower == 'bitsadmin' or name_lower == 'bitsadmin.exe':
            for arg in args:
                if arg.lower() == '/transfer':
                    return 'ask', 'Command downloads files via BITS transfer'
    
    return 'passthrough', None


def check_add_type(command_parts: list) -> tuple:
    """Check for Add-Type usage."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower == 'add-type':
            return 'ask', 'Command compiles and loads .NET code'
    return 'passthrough', None


def check_com_object(command_parts: list) -> tuple:
    """Check for New-Object -ComObject."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower != 'new-object':
            continue
        
        args = cmd.get('args', [])
        for arg in args:
            arg_lower = arg.lower()
            if arg_lower.startswith('-comobject') or arg_lower.startswith('-com'):
                return 'ask', 'Command instantiates a COM object which may have execution capabilities'
            if arg_lower == '-comobject' and len(arg) > 9:
                return 'ask', 'Command instantiates a COM object which may have execution capabilities'
    
    return 'passthrough', None


def check_dangerous_file_path_execution(command_parts: list) -> tuple:
    """Check for -FilePath execution via Invoke-Command, Start-Job, etc."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        args = cmd.get('args', [])
        
        if name_lower not in FILEPATH_EXECUTION_CMDLETS:
            continue
        
        for arg in args:
            arg_lower = arg.lower()
            if arg_lower.startswith('-filepath') or arg_lower.startswith('-literalpath'):
                return 'ask', f'{cmd.get("name")} -FilePath executes an arbitrary script file'
            if arg_lower == '-f' or arg_lower == '-l':
                return 'ask', f'{cmd.get("name")} -FilePath executes an arbitrary script file'
    
    return 'passthrough', None


def check_foreach_member_name(command_parts: list) -> tuple:
    """Check for ForEach-Object -MemberName."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower not in ('foreach-object', 'foreach', '%'):
            continue
        
        args = cmd.get('args', [])
        for arg in args:
            arg_lower = arg.lower()
            if arg_lower.startswith('-membername') or arg_lower == '-m':
                return 'ask', 'ForEach-Object -MemberName invokes methods by string name which cannot be validated'
    
    return 'passthrough', None


def check_start_process(command_parts: list) -> tuple:
    """Check for Start-Process with -Verb RunAs or PS executables."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower not in ('start-process', 'saps', 'start'):
            continue
        
        args = cmd.get('args', [])
        
        # Check for -Verb RunAs
        has_verb = False
        has_runas = False
        for arg in args:
            arg_lower = arg.lower()
            if arg_lower.startswith('-verb') or arg_lower == '-v':
                has_verb = True
            if arg_lower == 'runas':
                has_runas = True
        
        if has_verb and has_runas:
            return 'ask', 'Command requests elevated privileges'
        
        # Check for PowerShell executable as target
        for arg in args:
            if is_powershell_executable(arg.replace('"', '').replace("'", '')):
                return 'ask', 'Start-Process launches a nested PowerShell process which cannot be validated'
    
    return 'passthrough', None


def check_script_block_injection(command_parts: list) -> tuple:
    """Check for script block injection patterns."""
    has_script_blocks = False
    
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower in DANGEROUS_SCRIPT_BLOCK_CMDLETS:
            return 'ask', 'Command contains script block with dangerous cmdlet that may execute arbitrary code'
        if '{' in cmd.get('text', '') or '}' in cmd.get('text', ''):
            has_script_blocks = True
    
    # If all commands are safe script block consumers, allow
    all_safe = True
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower not in SAFE_SCRIPT_BLOCK_CMDLETS:
            all_safe = False
            break
    
    if all_safe:
        return 'passthrough', None
    
    if has_script_blocks:
        return 'ask', 'Command contains script block that may execute arbitrary code'
    
    return 'passthrough', None


def check_sub_expressions(command: str) -> tuple:
    """Check for subexpressions $()."""
    if '$(' in command:
        return 'ask', 'Command contains subexpressions $()'
    return 'passthrough', None


def check_expandable_strings(command: str) -> tuple:
    """Check for expandable strings with embedded expressions."""
    # Match double-quoted strings with $ inside
    if re.search(r'"[^"]*\$[^"]*"', command):
        return 'ask', 'Command contains expandable strings with embedded expressions'
    return 'passthrough', None


def check_splatting(command: str) -> tuple:
    """Check for splatting @variable."""
    # Match @variable pattern (not email addresses)
    if re.search(r'(?:^|[^\w.])@[\w]+', command):
        return 'ask', 'Command uses splatting (@variable)'
    return 'passthrough', None


def check_stop_parsing(command: str) -> tuple:
    """Check for stop-parsing token --%."""
    if '--%' in command:
        return 'ask', 'Command uses stop-parsing token (--%)'
    return 'passthrough', None


def check_member_invocations(command: str) -> tuple:
    """Check for .NET method invocations."""
    # Match .Method() pattern
    if re.search(r'\.\w+\s*\(', command):
        return 'ask', 'Command invokes .NET methods'
    return 'passthrough', None


def check_invoke_item(command_parts: list) -> tuple:
    """Check for Invoke-Item which opens files with default handler."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower == 'invoke-item' or name_lower == 'ii':
            return 'ask', 'Invoke-Item opens files with the default handler (ShellExecute). On executable files this runs arbitrary code.'
    return 'passthrough', None


def check_scheduled_task(command_parts: list) -> tuple:
    """Check for scheduled task creation/modification."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower in SCHEDULED_TASK_CMDLETS:
            return 'ask', f'{cmd.get("name")} creates or modifies a scheduled task (persistence primitive)'
        if name_lower in ('schtasks', 'schtasks.exe'):
            args = cmd.get('args', [])
            for arg in args:
                arg_lower = arg.lower()
                if arg_lower in ('/create', '/change', '-create', '-change'):
                    return 'ask', 'schtasks with create/change modifies scheduled tasks (persistence primitive)'
    return 'passthrough', None


def check_env_var_manipulation(command_parts: list, command: str) -> tuple:
    """Check for environment variable manipulation."""
    # Check for $env: in command
    if '$env:' in command.lower():
        for cmd in command_parts:
            name_lower = cmd.get('name', '').lower()
            if name_lower in ENV_WRITE_CMDLETS:
                return 'ask', 'Command modifies environment variables'
    
    # Check for assignments to env vars
    if re.search(r'\$env:\w+\s*=', command):
        return 'ask', 'Command modifies environment variables'
    
    return 'passthrough', None


def check_module_loading(command_parts: list) -> tuple:
    """Check for module loading cmdlets."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower in MODULE_LOADING_CMDLETS:
            return 'ask', 'Command loads, installs, or downloads a PowerShell module or script, which can execute arbitrary code'
    return 'passthrough', None


def check_runtime_state_manipulation(command_parts: list) -> tuple:
    """Check for alias/variable manipulation that affects future command resolution."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        # Strip module qualifier
        if '\\' in name_lower:
            name_lower = name_lower.split('\\')[-1]
        if name_lower in RUNTIME_STATE_CMDLETS:
            return 'ask', 'Command creates or modifies an alias or variable that can affect future command resolution'
    return 'passthrough', None


def check_wmi_process_spawn(command_parts: list) -> tuple:
    """Check for WMI/CIM method invocation that can spawn processes."""
    for cmd in command_parts:
        name_lower = cmd.get('name', '').lower()
        if name_lower in WMI_SPAWN_CMDLETS:
            return 'ask', f'{cmd.get("name")} can spawn arbitrary processes via WMI/CIM (Win32_Process Create)'
    return 'passthrough', None


def powershell_command_is_safe(command: str, parsed_command: Optional[dict] = None) -> dict:
    """
    Main entry point for PowerShell security validation.
    
    Args:
        command: The PowerShell command string
        parsed_command: Optional parsed AST from PowerShell parser
        
    Returns:
        Security result with behavior: 'passthrough', 'ask', or 'allow'
    """
    # If parsing failed (no parsed_command), return ask as safe default
    if not parsed_command:
        # Fallback to regex-based checks
        checks = [
            ('subexpressions', check_sub_expressions),
            ('expandable_strings', lambda c: check_expandable_strings(c)),
            ('splatting', check_splatting),
            ('stop_parsing', check_stop_parsing),
            ('member_invocations', check_member_invocations),
        ]
        
        for name, check_func in checks:
            behavior, msg = check_func(command)
            if behavior == 'ask':
                return {'behavior': 'ask', 'message': msg}
        
        return {'behavior': 'passthrough'}
    
    command_parts = parsed_command.get('commands', [])
    
    if not parsed_command.get('valid', True):
        return {'behavior': 'ask', 'message': 'Could not parse command for security analysis'}
    
    validators = [
        check_invoke_expression,
        check_dynamic_command_name,
        check_encoded_command,
        check_pwsh_command_or_file,
        check_download_cradles,
        check_download_utilities,
        check_add_type,
        check_com_object,
        check_dangerous_file_path_execution,
        check_foreach_member_name,
        check_start_process,
        check_script_block_injection,
    ]
    
    for validator in validators:
        behavior, msg = validator(command_parts)
        if behavior == 'ask':
            return {'behavior': 'ask', 'message': msg}
    
    # String-based checks
    string_checks = [
        check_sub_expressions,
        check_expandable_strings,
        check_splatting,
        check_stop_parsing,
        check_member_invocations,
    ]
    
    for check_func in string_checks:
        behavior, msg = check_func(command)
        if behavior == 'ask':
            return {'behavior': 'ask', 'message': msg}
    
    # Additional command-based checks
    additional_checks = [
        check_invoke_item,
        check_scheduled_task,
        check_env_var_manipulation,
        check_module_loading,
        check_runtime_state_manipulation,
        check_wmi_process_spawn,
    ]
    
    for validator in additional_checks:
        if validator in (check_env_var_manipulation,):
            behavior, msg = validator(command_parts, command)
        else:
            behavior, msg = validator(command_parts)
        if behavior == 'ask':
            return {'behavior': 'ask', 'message': msg}
    
    return {'behavior': 'passthrough'}