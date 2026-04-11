"""LSP Diagnostic Registry - stores and deduplicates LSP diagnostics."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from api_server.services.lsp.diagnostic_tracking import DiagnosticFile


MAX_DIAGNOSTICS_PER_FILE = 10
MAX_TOTAL_DIAGNOSTICS = 30
MAX_DELIVERED_FILES = 500


class PendingLSPDiagnostic:
    def __init__(
        self,
        server_name: str,
        files: List[DiagnosticFile],
        timestamp: float,
        attachment_sent: bool = False,
    ):
        self.server_name = server_name
        self.files = files
        self.timestamp = timestamp
        self.attachment_sent = attachment_sent


_pending_diagnostics: Dict[str, PendingLSPDiagnostic] = {}

_delivered_diagnostics: Dict[str, Set[str]] = {}


def _severity_to_number(severity: Optional[str]) -> int:
    if severity == "Error":
        return 1
    elif severity == "Warning":
        return 2
    elif severity == "Info":
        return 3
    elif severity == "Hint":
        return 4
    return 4


def _create_diagnostic_key(diag: DiagnosticFile) -> str:
    return json.dumps({
        "message": diag.get("message"),
        "severity": diag.get("severity"),
        "range": diag.get("range"),
        "source": diag.get("source") or None,
        "code": diag.get("code") or None,
    }, sort_keys=True)


def _deduplicate_diagnostic_files(
    all_files: List[DiagnosticFile],
) -> List[DiagnosticFile]:
    file_map: Dict[str, Set[str]] = {}
    deduped_files: List[DiagnosticFile] = []

    for file in all_files:
        uri = file["uri"]
        if uri not in file_map:
            file_map[uri] = set()
            deduped_files.append({"uri": uri, "diagnostics": []})

        seen_diagnostics = file_map[uri]
        deduped_file = next(f for f in deduped_files if f["uri"] == uri)
        previously_delivered = _delivered_diagnostics.get(uri, set())

        for diag in file["diagnostics"]:
            key = _create_diagnostic_key(diag)

            if key in seen_diagnostics or key in previously_delivered:
                continue

            seen_diagnostics.add(key)
            deduped_file["diagnostics"].append(diag)

    return [f for f in deduped_files if len(f["diagnostics"]) > 0]


def register_pending_diagnostic(
    server_name: str,
    files: List[DiagnosticFile],
) -> None:
    diagnostic_id = f"{server_name}_{datetime.now().timestamp()}_{len(_pending_diagnostics)}"

    _pending_diagnostics[diagnostic_id] = PendingLSPDiagnostic(
        server_name=server_name,
        files=files,
        timestamp=datetime.now().timestamp(),
        attachment_sent=False,
    )


def check_for_diagnostics() -> List[Dict[str, Any]]:
    all_files: List[DiagnosticFile] = []
    server_names: Set[str] = set()
    diagnostics_to_mark: List[PendingLSPDiagnostic] = []

    for diagnostic in _pending_diagnostics.values():
        if not diagnostic.attachment_sent:
            all_files.extend(diagnostic.files)
            server_names.add(diagnostic.server_name)
            diagnostics_to_mark.append(diagnostic)

    if not all_files:
        return []

    deduped_files = _deduplicate_diagnostic_files(all_files)

    for diagnostic in diagnostics_to_mark:
        diagnostic.attachment_sent = True

    ids_to_delete = [
        diag_id for diag_id, diag in _pending_diagnostics.items()
        if diag.attachment_sent
    ]
    for diag_id in ids_to_delete:
        del _pending_diagnostics[diag_id]

    total_diagnostics = 0
    truncated_count = 0

    for file in deduped_files:
        file["diagnostics"].sort(
            key=lambda d: _severity_to_number(d.get("severity"))
        )

        if len(file["diagnostics"]) > MAX_DIAGNOSTICS_PER_FILE:
            truncated_count += len(file["diagnostics"]) - MAX_DIAGNOSTICS_PER_FILE
            file["diagnostics"] = file["diagnostics"][:MAX_DIAGNOSTICS_PER_FILE]

        remaining_capacity = MAX_TOTAL_DIAGNOSTICS - total_diagnostics
        if len(file["diagnostics"]) > remaining_capacity:
            truncated_count += len(file["diagnostics"]) - remaining_capacity
            file["diagnostics"] = file["diagnostics"][:remaining_capacity]

        total_diagnostics += len(file["diagnostics"])

    deduped_files = [f for f in deduped_files if len(f["diagnostics"]) > 0]

    for file in deduped_files:
        uri = file["uri"]
        if uri not in _delivered_diagnostics:
            _delivered_diagnostics[uri] = set()

        delivered = _delivered_diagnostics[uri]
        for diag in file["diagnostics"]:
            delivered.add(_create_diagnostic_key(diag))

    final_count = sum(len(f["diagnostics"]) for f in deduped_files)

    if final_count == 0:
        return []

    return [{
        "serverName": ", ".join(sorted(server_names)),
        "files": deduped_files,
    }]


def clear_all_diagnostics() -> None:
    _pending_diagnostics.clear()


def reset_all_diagnostic_state() -> None:
    _pending_diagnostics.clear()
    _delivered_diagnostics.clear()


def clear_delivered_diagnostics_for_file(file_uri: str) -> None:
    if file_uri in _delivered_diagnostics:
        del _delivered_diagnostics[file_uri]


def get_pending_diagnostic_count() -> int:
    return len(_pending_diagnostics)


class DiagnosticRegistry:
    @staticmethod
    def register_pending(server_name: str, files: List[DiagnosticFile]) -> None:
        register_pending_diagnostic(server_name, files)

    @staticmethod
    def check() -> List[Dict[str, Any]]:
        return check_for_diagnostics()

    @staticmethod
    def clear_all() -> None:
        clear_all_diagnostics()

    @staticmethod
    def reset_all() -> None:
        reset_all_diagnostic_state()

    @staticmethod
    def clear_for_file(file_uri: str) -> None:
        clear_delivered_diagnostics_for_file(file_uri)

    @staticmethod
    def pending_count() -> int:
        return get_pending_diagnostic_count()
