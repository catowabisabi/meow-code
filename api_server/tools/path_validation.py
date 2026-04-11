"""
PowerShell-specific path validation for command arguments.

Extracts file paths from PowerShell commands and validates they stay
within allowed project directories.
"""

import os
import re
from typing import Optional

MAX_DIRS_TO_LIST = 5
GLOB_PATTERN_REGEX = re.compile(r'[*?[\]]')

DANGEROUS_REMOVAL_PATHS = {'/', '/etc', '/usr', '/bin', '/sbin', '/tmp', '/var', '/home'}

COMMON_SWITCHES = {'-verbose', '-debug'}
COMMON_VALUE_PARAMS = {
    '-erroraction', '-warningaction', '-informationaction', '-progressaction',
    '-errorvariable', '-warningvariable', '-informationvariable',
    '-outvariable', '-outbuffer', '-pipelinevariable',
}

CMDLET_PATH_CONFIG = {
    'set-content': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-passthru', '-force', '-whatif', '-confirm', '-usetransaction', '-nonewline', '-asbytestream'},
        'knownValueParams': {'-value', '-filter', '-include', '-exclude', '-credential', '-encoding', '-stream'},
    },
    'add-content': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-passthru', '-force', '-whatif', '-confirm', '-usetransaction', '-nonewline', '-asbytestream'},
        'knownValueParams': {'-value', '-filter', '-include', '-exclude', '-credential', '-encoding', '-stream'},
    },
    'remove-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-recurse', '-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential', '-stream'},
    },
    'clear-content': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential', '-stream'},
    },
    'out-file': {
        'operationType': 'write',
        'pathParams': {'-filepath', '-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-append', '-force', '-noclobber', '-nonewline', '-whatif', '-confirm'},
        'knownValueParams': {'-inputobject', '-encoding', '-width'},
    },
    'tee-object': {
        'operationType': 'write',
        'pathParams': {'-filepath', '-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-append'},
        'knownValueParams': {'-inputobject', '-variable', '-encoding'},
    },
    'export-csv': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-append', '-force', '-noclobber', '-notypeinformation', '-includetypeinformation', '-useculture', '-noheader', '-whatif', '-confirm'},
        'knownValueParams': {'-inputobject', '-delimiter', '-encoding', '-quotefields', '-usequotes'},
    },
    'export-clixml': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-noclobber', '-whatif', '-confirm'},
        'knownValueParams': {'-inputobject', '-depth', '-encoding'},
    },
    'new-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-itemtype', '-value', '-credential', '-type'},
        'leafOnlyPathParams': {'-name'},
    },
    'copy-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp', '-destination'},
        'knownSwitches': {'-container', '-force', '-passthru', '-recurse', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential', '-fromsession', '-tosession'},
    },
    'move-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp', '-destination'},
        'knownSwitches': {'-force', '-passthru', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential'},
    },
    'rename-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-passthru', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-newname', '-credential', '-filter', '-include', '-exclude'},
    },
    'set-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-passthru', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-value', '-credential', '-filter', '-include', '-exclude'},
    },
    'get-content': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-usetransaction', '-wait', '-raw', '-asbytestream'},
        'knownValueParams': {'-readcount', '-totalcount', '-tail', '-first', '-head', '-last', '-filter', '-include', '-exclude', '-credential', '-delimiter', '-encoding', '-stream'},
    },
    'get-childitem': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-recurse', '-force', '-name', '-usetransaction', '-followsymlink', '-directory', '-file', '-hidden', '-readonly', '-system'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-depth', '-attributes', '-credential'},
    },
    'get-item': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential', '-stream'},
    },
    'get-itemproperty': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-usetransaction'},
        'knownValueParams': {'-name', '-filter', '-include', '-exclude', '-credential'},
    },
    'get-itempropertyvalue': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-usetransaction'},
        'knownValueParams': {'-name', '-filter', '-include', '-exclude', '-credential'},
    },
    'get-filehash': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': set(),
        'knownValueParams': {'-algorithm', '-inputstream'},
    },
    'get-acl': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-audit', '-allcentralaccesspolicies', '-usetransaction'},
        'knownValueParams': {'-inputobject', '-filter', '-include', '-exclude'},
    },
    'format-hex': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-raw'},
        'knownValueParams': {'-inputobject', '-encoding', '-count', '-offset'},
    },
    'test-path': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-isvalid', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-pathtype', '-credential', '-olderthan', '-newerthan'},
    },
    'resolve-path': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-relative', '-usetransaction', '-force'},
        'knownValueParams': {'-credential', '-relativebasepath'},
    },
    'convert-path': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-usetransaction'},
        'knownValueParams': set(),
    },
    'select-string': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-simplematch', '-casesensitive', '-quiet', '-list', '-notmatch', '-allmatches', '-noemphasis', '-raw'},
        'knownValueParams': {'-inputobject', '-pattern', '-include', '-exclude', '-encoding', '-context', '-culture'},
    },
    'set-location': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-passthru', '-usetransaction'},
        'knownValueParams': {'-stackname'},
    },
    'push-location': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-passthru', '-usetransaction'},
        'knownValueParams': {'-stackname'},
    },
    'pop-location': {
        'operationType': 'read',
        'pathParams': set(),
        'knownSwitches': {'-passthru', '-usetransaction'},
        'knownValueParams': {'-stackname'},
    },
    'select-xml': {
        'operationType': 'read',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': set(),
        'knownValueParams': {'-xml', '-content', '-xpath', '-namespace'},
    },
    'get-winevent': {
        'operationType': 'read',
        'pathParams': {'-path'},
        'knownSwitches': {'-force', '-oldest'},
        'knownValueParams': {'-listlog', '-logname', '-listprovider', '-providername', '-maxevents', '-computername', '-credential', '-filterxpath', '-filterxml', '-filterhashtable'},
    },
    'invoke-webrequest': {
        'operationType': 'write',
        'pathParams': {'-outfile', '-infile'},
        'positionalSkip': 1,
        'optionalWrite': True,
        'knownSwitches': {'-allowinsecureredirect', '-allowunencryptedauthentication', '-disablekeepalive', '-nobodyprogress', '-passthru', '-preservefileauthorizationmetadata', '-resume', '-skipcertificatecheck', '-skipheadervalidation', '-skiphttperrorcheck', '-usebasicparsing', '-usedefaultcredentials'},
        'knownValueParams': {'-uri', '-method', '-body', '-contenttype', '-headers', '-maximumredirection', '-maximumretrycount', '-proxy', '-proxycredential', '-retryintervalsec', '-sessionvariable', '-timeoutsec', '-token', '-transferencoding', '-useragent', '-websession', '-credential', '-authentication', '-certificate', '-certificatethumbprint', '-form', '-httpversion'},
    },
    'invoke-restmethod': {
        'operationType': 'write',
        'pathParams': {'-outfile', '-infile'},
        'positionalSkip': 1,
        'optionalWrite': True,
        'knownSwitches': {'-allowinsecureredirect', '-allowunencryptedauthentication', '-disablekeepalive', '-followrellink', '-nobodyprogress', '-passthru', '-preservefileauthorizationmetadata', '-resume', '-skipcertificatecheck', '-skipheadervalidation', '-skiphttperrorcheck', '-usebasicparsing', '-usedefaultcredentials'},
        'knownValueParams': {'-uri', '-method', '-body', '-contenttype', '-headers', '-maximumfollowrellink', '-maximumredirection', '-maximumretrycount', '-proxy', '-proxycredential', '-retryintervalsec', '-sessionvariable', '-statuscodevariable', '-timeoutsec', '-token', '-transferencoding', '-useragent', '-websession', '-credential', '-authentication', '-certificate', '-certificatethumbprint', '-form', '-httpversion'},
    },
    'expand-archive': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp', '-destinationpath'},
        'knownSwitches': {'-force', '-passthru', '-whatif', '-confirm'},
        'knownValueParams': set(),
    },
    'compress-archive': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp', '-destinationpath'},
        'knownSwitches': {'-force', '-update', '-passthru', '-whatif', '-confirm'},
        'knownValueParams': {'-compressionlevel'},
    },
    'set-itemproperty': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-passthru', '-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-name', '-value', '-type', '-filter', '-include', '-exclude', '-credential', '-inputobject'},
    },
    'new-itemproperty': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-name', '-value', '-propertytype', '-type', '-filter', '-include', '-exclude', '-credential'},
    },
    'remove-itemproperty': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-name', '-filter', '-include', '-exclude', '-credential'},
    },
    'clear-item': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-force', '-whatif', '-confirm', '-usetransaction'},
        'knownValueParams': {'-filter', '-include', '-exclude', '-credential'},
    },
    'export-alias': {
        'operationType': 'write',
        'pathParams': {'-path', '-literalpath', '-pspath', '-lp'},
        'knownSwitches': {'-append', '-force', '-noclobber', '-passthru', '-whatif', '-confirm'},
        'knownValueParams': {'-name', '-description', '-scope', '-as'},
    },
}


def expand_tilde(file_path: str) -> str:
    if file_path == '~' or file_path.startswith('~/') or file_path.startswith('~\\'):
        return os.path.expanduser('~') + file_path[1:]
    return file_path


def is_dangerous_removal_raw_path(file_path: str) -> bool:
    expanded = expand_tilde(file_path.replace("'", '').replace('"', '')).replace('\\', '/')
    return expanded in DANGEROUS_REMOVAL_PATHS


def is_path_allowed(
    resolved_path: str,
    allowed_directories: Optional[list] = None,
    operation_type: str = 'read',
) -> tuple:
    allowed_directories = allowed_directories or []
    
    for dangerous in DANGEROUS_REMOVAL_PATHS:
        if resolved_path == dangerous or resolved_path.startswith(dangerous + '/'):
            return False, f'Path is in protected system path: {dangerous}'
    
    for allowed_dir in allowed_directories:
        if resolved_path.startswith(os.path.abspath(allowed_dir)):
            return True, 'Path is in allowed directory'
    
    return False, 'Path is not in allowed directories'


def check_path_constraints(
    command: str,
    allowed_directories: Optional[list] = None,
    cwd: Optional[str] = None,
) -> dict:
    allowed_directories = allowed_directories or []
    cwd = cwd or os.getcwd()
    
    operation_type = 'read'
    paths_to_check = []
    
    parts = _parse_command_parts(command)
    for cmd in parts:
        canonical = _resolve_to_canonical(cmd.get('name', ''))
        config = CMDLET_PATH_CONFIG.get(canonical)
        
        if not config:
            continue
        
        cmd_operation = config.get('operationType', 'read')
        if cmd_operation in ('write', 'create'):
            operation_type = 'write'
        
        paths = _extract_paths_from_command(cmd, config)
        paths_to_check.extend(paths)
    
    if not paths_to_check:
        return {'behavior': 'passthrough'}
    
    all_allowed = True
    disallowed_paths = []
    
    for path in paths_to_check:
        clean_path = expand_tilde(path.replace("'", '').replace('"', ''))
        normalized = clean_path.replace('\\', '/')
        
        if normalized.startswith('$') or '%' in normalized:
            all_allowed = False
            disallowed_paths.append(f'{path} (variable expansion)')
            continue
        
        if GLOB_PATTERN_REGEX.search(normalized):
            if operation_type in ('write', 'create'):
                all_allowed = False
                disallowed_paths.append(f'{path} (glob patterns not allowed in write operations)')
                continue
        
        if normalized.startswith('//') or normalized.startswith('\\\\'):
            all_allowed = False
            disallowed_paths.append(f'{path} (UNC paths blocked)')
            continue
        
        if '::' in normalized:
            all_allowed = False
            disallowed_paths.append(f'{path} (module-qualified paths blocked)')
            continue
        
        if ':' in normalized and len(normalized.split(':')[0]) >= 2:
            if normalized[1] == ':':
                pass
            else:
                all_allowed = False
                disallowed_paths.append(f'{path} (non-filesystem provider path)')
                continue
        
        abs_path = normalized if os.path.isabs(normalized) else os.path.join(cwd, normalized)
        
        allowed, reason = is_path_allowed(abs_path, allowed_directories, operation_type)
        if not allowed:
            all_allowed = False
            disallowed_paths.append(f'{path} ({reason})')
    
    if not paths_to_check:
        return {'behavior': 'passthrough'}
    
    if all_allowed:
        return {'behavior': 'passthrough'}
    
    return {
        'behavior': 'ask',
        'message': f'Path validation issues: {"; ".join(disallowed_paths[:5])}',
        'paths_checked': paths_to_check,
    }


def _resolve_to_canonical(name: str) -> str:
    COMMON_ALIASES = {
        'sl': 'set-location', 'cd': 'set-location', 'chdir': 'set-location',
        'pushd': 'push-location', 'popd': 'pop-location',
        'rm': 'remove-item', 'del': 'remove-item', 'rd': 'remove-item', 'ri': 'remove-item',
        'sc': 'set-content', 'gc': 'get-content', 'cat': 'get-content',
        'dir': 'get-childitem', 'ls': 'get-childitem', 'gci': 'get-childitem',
        'ni': 'new-item', 'mkdir': 'new-item',
        'cp': 'copy-item', 'copy': 'copy-item', 'cpi': 'copy-item',
        'mv': 'move-item', 'move': 'move-item', 'mi': 'move-item',
        'ren': 'rename-item', 'rni': 'rename-item',
        'si': 'set-item',
        'ac': 'add-content',
        '%': 'foreach-object', 'foreach': 'foreach-object',
        'iex': 'invoke-expression',
        'iwr': 'invoke-webrequest', 'irm': 'invoke-restmethod',
        'saps': 'start-process', 'start': 'start-process',
    }
    
    lower = name.lower()
    if lower in COMMON_ALIASES:
        return COMMON_ALIASES[lower]
    return lower


def _parse_command_parts(command: str) -> list:
    parts = []
    segments = re.split(r'\s*[;|]\s*', command)
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        
        tokens = segment.split()
        if not tokens:
            continue
        
        cmd_name = tokens[0]
        args = tokens[1:] if len(tokens) > 1 else []
        
        parts.append({
            'name': cmd_name,
            'args': args,
            'text': segment,
        })
    
    return parts


def _extract_paths_from_command(cmd: dict, config: dict) -> list:
    paths = []
    args = cmd.get('args', [])
    path_params = config.get('pathParams', set())
    known_switches = config.get('knownSwitches', set()) | COMMON_SWITCHES
    known_value_params = config.get('knownValueParams', set()) | COMMON_VALUE_PARAMS
    positional_skip = config.get('positionalSkip', 0)
    
    i = 0
    position = 0
    
    while i < len(args):
        arg = args[i]
        arg_lower = arg.lower()
        
        is_param = arg_lower.startswith('-') or arg_lower.startswith('/')
        
        if is_param:
            param_name = arg_lower.split(':')[0] if ':' in arg else arg_lower
            param_value = None
            
            if ':' in arg:
                param_value = arg.split(':', 1)[1]
            elif i + 1 < len(args):
                next_arg = args[i + 1]
                if not next_arg.lower().startswith('-') and not next_arg.lower().startswith('/'):
                    param_value = next_arg
                    i += 1
            
            if param_name in path_params and param_value:
                paths.append(param_value)
            elif param_name not in known_switches and param_name not in known_value_params:
                if param_value:
                    paths.append(param_value)
        else:
            if position >= positional_skip:
                paths.append(arg)
            position += 1
        
        i += 1
    
    return paths


def dangerous_removal_deny(path: str) -> dict:
    return {
        'behavior': 'deny',
        'message': f'Remove-Item on system path "{path}" is blocked. This path is protected from removal.',
        'decisionReason': {'type': 'other', 'reason': 'Removal targets a protected system path'},
    }