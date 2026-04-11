"""
PowerShell read-only command validation.

Cmdlets are case-insensitive; all matching is done in lowercase.
"""

import re
from typing import Optional

SAFE_OUTPUT_CMDLETS = {
    'out-null',
}

CMDLET_ALLOWLIST = {
    'get-childitem': {
        'safeFlags': {'-path', '-literalpath', '-filter', '-include', '-exclude', '-recurse', '-depth', '-name', '-force', '-attributes', '-directory', '-file', '-hidden', '-readonly', '-system'},
    },
    'get-content': {
        'safeFlags': {'-path', '-literalpath', '-totalcount', '-head', '-tail', '-raw', '-encoding', '-delimiter', '-readcount'},
    },
    'get-item': {
        'safeFlags': {'-path', '-literalpath', '-force', '-stream'},
    },
    'get-itemproperty': {
        'safeFlags': {'-path', '-literalpath', '-name'},
    },
    'test-path': {
        'safeFlags': {'-path', '-literalpath', '-pathtype', '-filter', '-include', '-exclude', '-isvalid', '-newerthan', '-olderthan'},
    },
    'resolve-path': {
        'safeFlags': {'-path', '-literalpath', '-relative'},
    },
    'get-filehash': {
        'safeFlags': {'-path', '-literalpath', '-algorithm', '-inputstream'},
    },
    'get-acl': {
        'safeFlags': {'-path', '-literalpath', '-audit', '-filter', '-include', '-exclude'},
    },
    'set-location': {
        'safeFlags': {'-path', '-literalpath', '-passsthru', '-stackname'},
    },
    'push-location': {
        'safeFlags': {'-path', '-literalpath', '-passsthru', '-stackname'},
    },
    'pop-location': {
        'safeFlags': {'-passsthru', '-stackname'},
    },
    'select-string': {
        'safeFlags': {'-path', '-literalpath', '-pattern', '-inputobject', '-simplematch', '-casesensitive', '-quiet', '-list', '-notmatch', '-allmatches', '-encoding', '-context', '-raw', '-noemphasis'},
    },
    'convertto-json': {
        'safeFlags': {'-inputobject', '-depth', '-compress', '-enumsasstrings', '-asarray'},
    },
    'convertfrom-json': {
        'safeFlags': {'-inputobject', '-depth', '-ashashtable', '-noenumerate'},
    },
    'convertto-csv': {
        'safeFlags': {'-inputobject', '-delimiter', '-notypeinformation', '-noheader', '-usequotes'},
    },
    'convertfrom-csv': {
        'safeFlags': {'-inputobject', '-delimiter', '-header', '-useculture'},
    },
    'convertto-xml': {
        'safeFlags': {'-inputobject', '-depth', '-as', '-notypeinformation'},
    },
    'convertto-html': {
        'safeFlags': {'-inputobject', '-property', '-head', '-title', '-body', '-pre', '-post', '-as', '-fragment'},
    },
    'format-hex': {
        'safeFlags': {'-path', '-literalpath', '-inputobject', '-encoding', '-count', '-offset'},
    },
    'get-member': {
        'safeFlags': {'-inputobject', '-membertype', '-name', '-static', '-view', '-force'},
    },
    'get-unique': {
        'safeFlags': {'-inputobject', '-asstring', '-caseinsensitive', '-ontype'},
    },
    'compare-object': {
        'safeFlags': {'-referenceobject', '-differenceobject', '-property', '-syncwindow', '-casesensitive', '-culture', '-excludedifferent', '-includeequal', '-passthru'},
    },
    'join-string': {
        'safeFlags': {'-inputobject', '-property', '-separator', '-outputprefix', '-outputsuffix', '-singlequote', '-doublequote', '-formatstring'},
    },
    'get-random': {
        'safeFlags': {'-inputobject', '-minimum', '-maximum', '-count', '-setseed', '-shuffle'},
    },
    'convert-path': {
        'safeFlags': {'-path', '-literalpath'},
    },
    'join-path': {
        'safeFlags': {'-path', '-childpath', '-additionalchildpath'},
    },
    'split-path': {
        'safeFlags': {'-path', '-literalpath', '-qualifier', '-noqualifier', '-parent', '-leaf', '-leafbase', '-extension', '-isabsolute'},
    },
    'get-hotfix': {
        'safeFlags': {'-id', '-description'},
    },
    'get-itempropertyvalue': {
        'safeFlags': {'-path', '-literalpath', '-name'},
    },
    'get-psprovider': {
        'safeFlags': {'-psprovider'},
    },
    'get-process': {
        'safeFlags': {'-name', '-id', '-module', '-fileversioninfo', '-includeusername'},
    },
    'get-service': {
        'safeFlags': {'-name', '-displayname', '-dependentservices', '-requiredservices', '-include', '-exclude'},
    },
    'get-computerinfo': {
        'allowAllFlags': True,
    },
    'get-host': {
        'allowAllFlags': True,
    },
    'get-date': {
        'safeFlags': {'-date', '-format', '-uformat', '-displayhint', '-asutc'},
    },
    'get-location': {
        'safeFlags': {'-psprovider', '-psdrive', '-stack', '-stackname'},
    },
    'get-psdrive': {
        'safeFlags': {'-name', '-psprovider', '-scope'},
    },
    'get-module': {
        'safeFlags': {'-name', '-listavailable', '-all', '-fullyqualifiedname', '-psedition'},
    },
    'get-alias': {
        'safeFlags': {'-name', '-definition', '-scope', '-exclude'},
    },
    'get-history': {
        'safeFlags': {'-id', '-count'},
    },
    'get-culture': {
        'allowAllFlags': True,
    },
    'get-uiculture': {
        'allowAllFlags': True,
    },
    'get-timezone': {
        'safeFlags': {'-name', '-id', '-listavailable'},
    },
    'get-uptime': {
        'allowAllFlags': True,
    },
    'write-output': {
        'safeFlags': {'-inputobject', '-noenumerate'},
    },
    'write-host': {
        'safeFlags': {'-object', '-nonewline', '-separator', '-foregroundcolor', '-backgroundcolor'},
    },
    'start-sleep': {
        'safeFlags': {'-seconds', '-milliseconds', '-duration'},
    },
    'format-table': {
        'allowAllFlags': True,
    },
    'format-list': {
        'allowAllFlags': True,
    },
    'format-wide': {
        'allowAllFlags': True,
    },
    'format-custom': {
        'allowAllFlags': True,
    },
    'measure-object': {
        'allowAllFlags': True,
    },
    'select-object': {
        'allowAllFlags': True,
    },
    'sort-object': {
        'allowAllFlags': True,
    },
    'group-object': {
        'allowAllFlags': True,
    },
    'where-object': {
        'allowAllFlags': True,
    },
    'out-string': {
        'allowAllFlags': True,
    },
    'out-host': {
        'allowAllFlags': True,
    },
    'get-netadapter': {
        'safeFlags': {'-name', '-interfacedescription', '-interfaceindex', '-physical'},
    },
    'get-netipaddress': {
        'safeFlags': {'-interfaceindex', '-interfacealias', '-addressfamily', '-type'},
    },
    'get-netipconfiguration': {
        'safeFlags': {'-interfaceindex', '-interfacealias', '-detailed', '-all'},
    },
    'get-netroute': {
        'safeFlags': {'-interfaceindex', '-interfacealias', '-addressfamily', '-destinationprefix'},
    },
    'get-dnsclientcache': {
        'safeFlags': {'-entry', '-name', '-type', '-status', '-section', '-data'},
    },
    'get-dnsclient': {
        'safeFlags': {'-interfaceindex', '-interfacealias'},
    },
    'get-eventlog': {
        'safeFlags': {'-logname', '-newest', '-after', '-before', '-entrytype', '-index', '-instanceid', '-message', '-source', '-username', '-asbaseobject', '-list'},
    },
    'get-winevent': {
        'safeFlags': {'-logname', '-listlog', '-listprovider', '-providername', '-path', '-maxevents', '-filterxpath', '-force', '-oldest'},
    },
    'get-cimclass': {
        'safeFlags': {'-classname', '-namespace', '-methodname', '-propertyname', '-qualifiername'},
    },
    'git': {},
    'gh': {},
    'docker': {},
    'ipconfig': {
        'safeFlags': {'/all', '/displaydns', '/allcompartments'},
    },
    'netstat': {
        'safeFlags': {'-a', '-b', '-e', '-f', '-n', '-o', '-p', '-q', '-r', '-s', '-t', '-x', '-y'},
    },
    'systeminfo': {
        'safeFlags': {'/fo', '/nh'},
    },
    'tasklist': {
        'safeFlags': {'/m', '/svc', '/v', '/fi', '/fo', '/nh'},
    },
    'where.exe': {
        'allowAllFlags': True,
    },
    'hostname': {
        'safeFlags': {'-a', '-d', '-f', '-i', '-I', '-s', '-y', '-A'},
    },
    'whoami': {
        'safeFlags': {'/user', '/groups', '/claims', '/priv', '/logonid', '/all', '/fo', '/nh'},
    },
    'ver': {
        'allowAllFlags': True,
    },
    'arp': {
        'safeFlags': {'-a', '-g', '-v', '-N'},
    },
    'route': {
        'safeFlags': {'print', 'PRINT', '-4', '-6'},
    },
    'getmac': {
        'safeFlags': {'/fo', '/nh', '/v'},
    },
    'file': {
        'safeFlags': {'-b', '--brief', '-i', '--mime', '-L', '--dereference', '--mime-type', '--mime-encoding', '-z', '--uncompress', '-p', '--preserve-date', '-k', '--keep-going', '-r', '--raw', '-v', '--version', '-0', '--print0', '-s', '--special-files', '-l', '-F', '--separator', '-e', '-P', '-N', '--no-pad', '-E', '--extension'},
    },
    'tree': {
        'safeFlags': {'/F', '/A', '/Q', '/L'},
    },
    'findstr': {
        'safeFlags': {'/B', '/E', '/L', '/R', '/S', '/I', '/X', '/V', '/N', '/M', '/O', '/P', '/C', '/G', '/D', '/A'},
    },
    'dotnet': {},
}

SAFE_EXTERNAL_EXES = {'where.exe'}

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


def resolve_to_canonical(name: str) -> str:
    lower = name.lower()
    if lower in COMMON_ALIASES:
        return COMMON_ALIASES[lower]
    return lower


def is_safe_output_command(name: str) -> bool:
    canonical = resolve_to_canonical(name)
    return canonical in SAFE_OUTPUT_CMDLETS


def has_sync_security_concerns(command: str) -> bool:
    trimmed = command.strip()
    if not trimmed:
        return False
    
    if '$(' in trimmed:
        return True
    
    if re.search(r'(?:^|[^\w.])@[\w]+', trimmed):
        return True
    
    if re.search(r'\.\w+\s*\(', trimmed):
        return True
    
    if re.search(r'\$[\w]+\s*[+\-*/]?=', trimmed):
        return True
    
    if '--%' in trimmed:
        return True
    
    if '\\\\' in trimmed or re.search(r'(?<!:)\/\/', trimmed):
        return True
    
    if '::' in trimmed:
        return True
    
    return False


def is_read_only_command(command: str, parsed: Optional[dict] = None) -> bool:
    trimmed_command = command.strip()
    if not trimmed_command:
        return False
    
    if has_sync_security_concerns(trimmed_command):
        return False
    
    parts = _parse_command_parts(trimmed_command)
    if not parts:
        return False
    
    for cmd in parts:
        name = cmd.get('name', '')
        canonical = resolve_to_canonical(name)
        
        if is_safe_output_command(canonical):
            continue
        
        config = CMDLET_ALLOWLIST.get(canonical)
        if not config:
            return False
        
        if config.get('allowAllFlags', False):
            continue
        
        safe_flags = config.get('safeFlags', set())
        args = cmd.get('args', [])
        
        i = 0
        while i < len(args):
            arg = args[i]
            arg_lower = arg.lower()
            
            if arg_lower.startswith('-') or arg_lower.startswith('/'):
                param_name = arg_lower.split(':')[0]
                
                if param_name not in safe_flags:
                    return False
                
                if ':' not in arg and i + 1 < len(args):
                    next_arg = args[i + 1]
                    if not next_arg.lower().startswith('-') and not next_arg.lower().startswith('/'):
                        i += 1
            
            i += 1
    
    return True


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


def is_cwd_changing_cmdlet(name: str) -> bool:
    canonical = resolve_to_canonical(name)
    return canonical in ('set-location', 'push-location', 'pop-location', 'new-psdrive')