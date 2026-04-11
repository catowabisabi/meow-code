"""LSP passive feedback - diagnostic notifications from LSP servers."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from api_server.services.lsp.diagnostic_registry import register_pending_diagnostic
from api_server.services.lsp.diagnostic_tracking import DiagnosticFile
from api_server.services.lsp.manager import LSPServerManager


# Type for a single diagnostic
Diagnostic = Dict[str, Any]


@dataclass
class DiagnosticFeedback:
    """Feedback data from LSP publishDiagnostics notification."""
    uri: str
    diagnostics: List[Diagnostic]
    timestamp: datetime = field(default_factory=datetime.now)


def _map_lsp_severity(lsp_severity: Optional[int]) -> str:
    if lsp_severity == 1:
        return "Error"
    elif lsp_severity == 2:
        return "Warning"
    elif lsp_severity == 3:
        return "Info"
    elif lsp_severity == 4:
        return "Hint"
    return "Error"


def _format_diagnostics_for_attachment(
    params: Dict[str, Any],
) -> List[DiagnosticFile]:
    uri = params.get("uri", "")

    if uri.startswith("file://"):
        try:
            uri = Path(uri).resolve().as_posix()
        except Exception:
            pass

    diagnostics = []
    for diag in params.get("diagnostics", []):
        range_data = diag.get("range", {})
        start = range_data.get("start", {"line": 0, "character": 0})
        end = range_data.get("end", {"line": 0, "character": 0})

        lsp_severity = diag.get("severity")
        code = diag.get("code")
        if code is not None:
            code = str(code)

        formatted_diag = {
            "message": diag.get("message", ""),
            "severity": _map_lsp_severity(lsp_severity),
            "range": {
                "start": {
                    "line": start.get("line", 0),
                    "character": start.get("character", 0),
                },
                "end": {
                    "line": end.get("line", 0),
                    "character": end.get("character", 0),
                },
            },
            "source": diag.get("source"),
            "code": code,
        }
        diagnostics.append(formatted_diag)

    return [{"uri": uri, "diagnostics": diagnostics}]


class HandlerRegistrationResult:
    def __init__(
        self,
        total_servers: int,
        success_count: int,
        registration_errors: List[Dict[str, str]],
        diagnostic_failures: Dict[str, Dict[str, Any]],
    ):
        self.total_servers = total_servers
        self.success_count = success_count
        self.registration_errors = registration_errors
        self.diagnostic_failures = diagnostic_failures


def register_lsp_notification_handlers(
    manager: LSPServerManager,
) -> HandlerRegistrationResult:
    servers = manager.get_all_servers()

    registration_errors: List[Dict[str, str]] = []
    success_count = 0
    diagnostic_failures: Dict[str, Dict[str, Any]] = {}

    for server_name, server_instance in servers.items():
        try:
            if server_instance is None or not hasattr(server_instance, "on_notification"):
                registration_errors.append({
                    "serverName": server_name,
                    "error": "Server instance has no onNotification method",
                })
                continue

            def create_handler(srv_name: str):
                def handler(params: Any) -> None:
                    try:
                        if not params or not isinstance(params, dict):
                            return
                        if "uri" not in params or "diagnostics" not in params:
                            return

                        diagnostic_files = _format_diagnostics_for_attachment(params)

                        first_file = diagnostic_files[0] if diagnostic_files else None
                        if not first_file or not first_file["diagnostics"]:
                            return

                        register_pending_diagnostic(
                            server_name=srv_name,
                            files=diagnostic_files,
                        )

                        if srv_name in diagnostic_failures:
                            del diagnostic_failures[srv_name]

                    except Exception:
                        failures = diagnostic_failures.get(srv_name, {"count": 0, "lastError": ""})
                        failures["count"] = failures.get("count", 0) + 1
                        failures["lastError"] = str(Exception())
                        diagnostic_failures[srv_name] = failures

                return handler

            server_instance.on_notification(
                "textDocument/publishDiagnostics",
                create_handler(server_name),
            )
            success_count += 1

        except Exception as e:
            registration_errors.append({
                "serverName": server_name,
                "error": str(e),
            })

    return HandlerRegistrationResult(
        total_servers=len(servers),
        success_count=success_count,
        registration_errors=registration_errors,
        diagnostic_failures=diagnostic_failures,
    )


class PassiveFeedbackHandler:
    def __init__(self, lsp_client: LSPServerManager):
        self.lsp_client = lsp_client
        self._feedback_handlers: List[Callable[[DiagnosticFeedback], None]] = []
        self._diagnostics_by_uri: Dict[str, List[Diagnostic]] = {}

    def register_feedback_handler(
        self, handler: Callable[[DiagnosticFeedback], None]
    ) -> None:
        self._feedback_handlers.append(handler)

    async def handle_publish_diagnostics(
        self, uri: str, diagnostics: List[Dict[str, Any]]
    ) -> None:
        feedback = DiagnosticFeedback(uri=uri, diagnostics=diagnostics)
        self._diagnostics_by_uri[uri] = diagnostics
        for handler in self._feedback_handlers:
            handler(feedback)

    def get_diagnostics(self, uri: str) -> List[Diagnostic]:
        return self._diagnostics_by_uri.get(uri, [])

    def clear_diagnostics(self, uri: str) -> None:
        if uri in self._diagnostics_by_uri:
            del self._diagnostics_by_uri[uri]

    def get_all_diagnostics(self) -> Dict[str, List[Diagnostic]]:
        return dict(self._diagnostics_by_uri)
