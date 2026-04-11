import re

CANONICAL_COMMANDS: dict[str, str] = {
    "sl": "set-location",
    "cd": "set-location",
    "chdir": "set-location",
    "pushd": "push-location",
    "popd": "pop-location",
    "rd": "remove-item",
    "rm": "remove-item",
    "del": "remove-item",
    "ri": "remove-item",
    "rmdir": "remove-item",
    "cp": "copy-item",
    "copy": "copy-item",
    "cpi": "copy-item",
    "mv": "move-item",
    "move": "move-item",
    "mi": "move-item",
    "ren": "rename-item",
    "rni": "rename-item",
    "cat": "get-content",
    "gc": "get-content",
    "type": "get-content",
    "dir": "get-childitem",
    "ls": "get-childitem",
    "gci": "get-childitem",
    "gl": "get-location",
    "pwd": "get-location",
    "gi": "get-item",
    "ni": "new-item",
    "md": "mkdir",
    "mkdir": "new-item",
    "echo": "write-output",
    "write": "write-output",
    "owl": "out-file",
    "sc": "set-content",
    "ac": "add-content",
    "gcm": "get-command",
    "gdr": "get-childitem",
    "gm": "get-member",
    "gps": "get-process",
    "ps": "get-process",
    "gsv": "get-service",
    "svc": "get-service",
    "fh": "get-filehash",
    "gacl": "get-acl",
    "fhx": "format-hex",
    "saps": "start-process",
    "start": "start-process",
    "kill": "stop-process",
    "spps": "stop-process",
    "stop": "stop-process",
    "gcim": "get-ciminstance",
    "gwmi": "get-wmiobject",
    "iex": "invoke-expression",
    "irm": "invoke-restmethod",
    "iwr": "invoke-webrequest",
    "curl": "invoke-webrequest",
    "wget": "invoke-webrequest",
    "curl.exe": "invoke-webrequest",
    "wget.exe": "invoke-webrequest",
}

WINDOWS_PATHEXT_PATTERN = re.compile(r"\.(exe|cmd|bat|com)$", re.IGNORECASE)


def resolve_to_canonical(name: str) -> str:
    lower = name.lower()
    if not ("\\" in lower or "/" in lower):
        lower = WINDOWS_PATHEXT_PATTERN.sub("", lower)
    if lower in CANONICAL_COMMANDS:
        return CANONICAL_COMMANDS[lower]
    return lower


PS_SEARCH_COMMANDS: set[str] = {
    "select-string",
    "get-childitem",
    "findstr",
    "where.exe",
}

PS_READ_COMMANDS: set[str] = {
    "get-content",
    "get-item",
    "test-path",
    "resolve-path",
    "get-process",
    "get-service",
    "get-location",
    "get-filehash",
    "get-acl",
    "format-hex",
}

PS_SEMANTIC_NEUTRAL_COMMANDS: set[str] = {
    "write-output",
    "write-host",
}