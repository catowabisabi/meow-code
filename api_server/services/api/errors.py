import re
from typing import Optional, Any, Dict


API_ERROR_MESSAGE_PREFIX = "API Error"
PROMPT_TOO_LONG_ERROR_MESSAGE = "Prompt is too long"
INVALID_API_KEY_ERROR_MESSAGE = "Not logged in · Please run /login"
INVALID_API_KEY_ERROR_MESSAGE_EXTERNAL = "Invalid API key · Fix external API key"
TOKEN_REVOKED_ERROR_MESSAGE = "OAuth token revoked · Please run /login"
REPEATED_529_ERROR_MESSAGE = "Repeated 529 Overloaded errors"
CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE = "Credit balance is too low"
CCR_AUTH_ERROR_MESSAGE = "Authentication error · This may be a temporary network issue, please try again"


def starts_with_api_error_prefix(text: str) -> bool:
    return (
        text.startswith(API_ERROR_MESSAGE_PREFIX) or
        text.startswith(f"Please run /login · {API_ERROR_MESSAGE_PREFIX}")
    )


def is_prompt_too_long_message(msg: Dict[str, Any]) -> bool:
    if not msg.get("isApiErrorMessage"):
        return False
    content = msg.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return False
    return any(
        block.get("type") == "text" and
        block.get("text", "").startswith(PROMPT_TOO_LONG_ERROR_MESSAGE)
        for block in content
    )


def parse_prompt_too_long_token_counts(raw_message: str) -> Dict[str, Optional[int]]:
    match = re.search(
        r"prompt is too long[^0-9]*(\d+)\s*tokens?\s*>\s*(\d+)",
        raw_message,
        re.IGNORECASE,
    )
    if match:
        return {
            "actual_tokens": int(match.group(1)),
            "limit_tokens": int(match.group(2)),
        }
    return {"actual_tokens": None, "limit_tokens": None}


def is_media_size_error(raw: str) -> bool:
    raw_lower = raw.lower()
    return (
        ("image exceeds" in raw_lower and "maximum" in raw_lower) or
        ("image dimensions exceed" in raw_lower and "many-image" in raw_lower) or
        bool(re.search(r"maximum of \d+ PDF pages", raw))
    )


def classify_api_error(error: Any) -> str:
    if isinstance(error, Exception):
        message = str(error)
        
        if message == "Request was aborted.":
            return "aborted"
        
        if "timeout" in message.lower():
            return "api_timeout"
        
        if REPEATED_529_ERROR_MESSAGE in message:
            return "repeated_529"
        
        if "image exceeds" in message.lower() and "maximum" in message.lower():
            return "image_too_large"
        
        if "image dimensions exceed" in message.lower() and "many-image" in message.lower():
            return "image_too_large"
        
        if re.search(r"maximum of \d+ PDF pages", message):
            return "pdf_too_large"
        
        if "The PDF specified is password protected" in message:
            return "pdf_password_protected"
        
        if "tool_use" in message and "ids were found without" in message:
            return "tool_use_mismatch"
        
        if "unexpected" in message and "tool_use_id" in message:
            return "unexpected_tool_result"
        
        if "duplicate" in message and "tool_use" in message:
            return "duplicate_tool_use_id"
        
        if "x-api-key" in message.lower():
            return "invalid_api_key"
        
        if "credit balance is too low" in message.lower():
            return "credit_balance_low"
        
        if "prompt is too long" in message.lower():
            return "prompt_too_long"
        
        if "invalid model name" in message.lower():
            return "invalid_model"
    
    if isinstance(error, dict):
        status = error.get("status")
        message = error.get("message", "")
        
        if status == 429:
            return "rate_limit"
        
        if status == 529 or '"type":"overloaded_error"' in message:
            return "server_overload"
        
        if status == 401 or status == 403:
            if "OAuth token has been revoked" in message:
                return "token_revoked"
            if "OAuth authentication is currently not allowed" in message:
                return "oauth_org_not_allowed"
            return "auth_error"
        
        if status == 400:
            if "image exceeds" in message.lower() and "maximum" in message.lower():
                return "image_too_large"
            if "image dimensions exceed" in message.lower() and "many-image" in message.lower():
                return "image_too_large"
            if "tool_use" in message and "ids were found without" in message:
                return "tool_use_mismatch"
            if "unexpected" in message and "tool_use_id" in message:
                return "unexpected_tool_result"
            if "duplicate" in message and "tool_use" in message:
                return "duplicate_tool_use_id"
            if "invalid model name" in message.lower():
                return "invalid_model"
            if "organization has been disabled" in message.lower():
                return "org_disabled"
        
        if status == 404:
            return "not_found"
        
        if status == 413:
            return "request_too_large"
        
        if status and status >= 500:
            return "server_error"
        
        if status and status >= 400:
            return "client_error"
    
    return "unknown"


def get_assistant_message_from_error(
    error: Any,
    model: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    options = options or {}
    
    if isinstance(error, Exception):
        message = str(error)
        
        if "timeout" in message.lower():
            return _create_error_message("Request timed out", "unknown")
        
        if "image exceeds" in message.lower() and "maximum" in message.lower():
            return _create_error_message("Image was too large. Double press esc to go back and try again with a smaller image.")
        
        if "image dimensions exceed" in message.lower() and "many-image" in message.lower():
            return _create_error_message(
                "An image in the conversation exceeds the dimension limit for many-image requests (2000px). Run /compact to remove old images from context, or start a new session."
            )
        
        if re.search(r"maximum of \d+ PDF pages", message):
            return _create_error_message(
                "PDF too large (max pages, max size). Double press esc to go back and try again, or use pdftotext to convert to text first."
            )
        
        if "The PDF specified is password protected" in message:
            return _create_error_message(
                "PDF is password protected. Please double press esc to edit your message and try again."
            )
        
        if "The PDF specified was not valid" in message:
            return _create_error_message(
                "The PDF file was not valid. Double press esc to go back and try again with a different file."
            )
        
        if "tool_use" in message and "ids were found without" in message:
            return _create_error_message(
                "API Error: 400 due to tool use concurrency issues. Run /rewind to recover the conversation."
            )
        
        if "duplicate" in message and "tool_use" in message:
            return _create_error_message(
                "API Error: 400 duplicate tool_use ID in conversation history. Run /rewind to recover the conversation."
            )
        
        if "invalid model name" in message.lower():
            if "opus" in model.lower():
                return _create_error_message(
                    "Claude Opus is not available with the Claude Pro plan. If you have updated your subscription plan recently, run /logout and /login for the plan to take effect."
                )
            return _create_error_message(
                f"There's an issue with the selected model ({model}). Run /model to pick a different model."
            )
        
        if "credit balance is too low" in message.lower():
            return _create_error_message(CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE, "billing_error")
        
        if "organization has been disabled" in message.lower():
            return _create_error_message(
                "Your ANTHROPIC_API_KEY belongs to a disabled organization · Update or unset the environment variable"
            )
        
        if "x-api-key" in message.lower():
            return _create_error_message(INVALID_API_KEY_ERROR_MESSAGE, "authentication_failed")
        
        if "OAuth token has been revoked" in message:
            return _create_error_message(TOKEN_REVOKED_ERROR_MESSAGE, "authentication_failed")
        
        if "OAuth authentication is currently not allowed" in message:
            return _create_error_message(
                "Your account does not have access to Claude Code. Please run /login."
            )
        
        if "prompt is too long" in message.lower():
            return _create_error_message(
                PROMPT_TOO_LONG_ERROR_MESSAGE,
                "invalid_request",
                error_details=message,
            )
        
        return _create_error_message(f"{API_ERROR_MESSAGE_PREFIX}: {message}")
    
    if isinstance(error, dict):
        status = error.get("status")
        message = error.get("message", "")
        
        if status == 429:
            return _create_error_message(
                f"{API_ERROR_MESSAGE_PREFIX}: Request rejected (429) · {message or 'this may be a temporary capacity issue — check status.anthropic.com'}",
                "rate_limit",
            )
        
        if status == 401 or status == 403:
            return _create_error_message(
                f"Please run /login · {API_ERROR_MESSAGE_PREFIX}: {message}",
                "authentication_failed",
            )
        
        if status == 404:
            return _create_error_message(
                f"There's an issue with the selected model ({model}). Run /model to pick a different model."
            )
        
        if status == 413:
            return _create_error_message(
                "Request too large. Double press esc to go back and try with a smaller file."
            )
        
        if status == 400:
            if "image exceeds" in message.lower() and "maximum" in message.lower():
                return _create_error_message(
                    "Image was too large. Double press esc to go back and try again with a smaller image.",
                    error_details=message,
                )
            if "image dimensions exceed" in message.lower() and "many-image" in message.lower():
                return _create_error_message(
                    "An image in the conversation exceeds the dimension limit for many-image requests (2000px).",
                    error_details=message,
                )
            if "tool_use" in message and "ids were found without" in message:
                return _create_error_message(
                    "API Error: 400 due to tool use concurrency issues. Run /rewind to recover the conversation."
                )
            if "duplicate" in message and "tool_use" in message:
                return _create_error_message(
                    "API Error: 400 duplicate tool_use ID in conversation history. Run /rewind to recover the conversation.",
                    error_details=message,
                )
            if "invalid model name" in message.lower():
                return _create_error_message(
                    f"There's an issue with the selected model ({model}). Run /model to pick a different model."
                )
            if "organization has been disabled" in message.lower():
                return _create_error_message(
                    "Your ANTHROPIC_API_KEY belongs to a disabled organization · Update or unset the environment variable"
                )
            if "prompt is too long" in message.lower():
                return _create_error_message(
                    PROMPT_TOO_LONG_ERROR_MESSAGE,
                    "invalid_request",
                    error_details=message,
                )
        
        if status and status >= 500:
            return _create_error_message(
                f"{API_ERROR_MESSAGE_PREFIX}: {message}",
            )
        
        return _create_error_message(f"{API_ERROR_MESSAGE_PREFIX}: {message}")
    
    return _create_error_message(API_ERROR_MESSAGE_PREFIX)


def _create_error_message(
    content: str,
    error_type: str = "unknown",
    error_details: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "isApiErrorMessage": True,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
        },
        "error": error_type,
        "errorDetails": error_details,
    }
