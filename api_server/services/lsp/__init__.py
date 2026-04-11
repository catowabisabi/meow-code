"""LSP Service - Language Server Protocol implementation.

This module provides LSP client, server instance, and manager functionality
for communicating with language server processes via JSON-RPC over stdio.
"""

from api_server.services.lsp.client import LSPClient, create_lsp_client
from api_server.services.lsp.server_instance import LSPServerInstance, create_lsp_server_instance
from api_server.services.lsp.manager import (
    LSPServerManager,
    create_lsp_server_manager,
    InitializationState,
    InitializationStatus,
    get_lsp_server_manager,
    get_initialization_status,
    is_lsp_connected,
    wait_for_initialization,
    initialize_lsp_server_manager,
    reinitialize_lsp_server_manager,
    shutdown_lsp_server_manager,
    _reset_lsp_manager_for_testing,
)
from api_server.services.lsp.diagnostic_registry import (
    DiagnosticRegistry,
    register_pending_diagnostic,
    check_for_diagnostics,
    clear_all_diagnostics,
    reset_all_diagnostic_state,
    clear_delivered_diagnostics_for_file,
    get_pending_diagnostic_count,
)
from api_server.services.lsp.passive_feedback import (
    register_lsp_notification_handlers,
)

__all__ = [
    # Client
    "LSPClient",
    "create_lsp_client",
    # Server Instance
    "LSPServerInstance",
    "create_lsp_server_instance",
    # Manager
    "LSPServerManager",
    "create_lsp_server_manager",
    "InitializationState",
    "InitializationStatus",
    "get_lsp_server_manager",
    "get_initialization_status",
    "is_lsp_connected",
    "wait_for_initialization",
    "initialize_lsp_server_manager",
    "reinitialize_lsp_server_manager",
    "shutdown_lsp_server_manager",
    "_reset_lsp_manager_for_testing",
    # Diagnostic Registry
    "DiagnosticRegistry",
    "register_pending_diagnostic",
    "check_for_diagnostics",
    "clear_all_diagnostics",
    "reset_all_diagnostic_state",
    "clear_delivered_diagnostics_for_file",
    "get_pending_diagnostic_count",
    # Passive Feedback
    "register_lsp_notification_handlers",
]
