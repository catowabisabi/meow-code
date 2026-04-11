"""WebFetchTool — fetch and extract content from a URL."""
import html
import re
from typing import Any, Dict

import httpx

from .types import ToolDef, ToolResult, ToolContext

MAX_CONTENT_SIZE = 50000
FETCH_TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
USER_AGENT = 'Mozilla/5.0 (compatible; AICodeAssistant/1.0)'

PREAPPROVED_HOSTS = {"github.com", "stackoverflow.com", "docs.python.org", "python.org", "npmjs.com", "pypi.org"}


def is_preapproved_host(hostname: str) -> bool:
    return hostname in PREAPPROVED_HOSTS


def extract_text(html_content: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "The URL to fetch content from"},
        "prompt": {"type": "string", "description": "The prompt to run on the fetched content"},
    },
    "required": ["url"],
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    url = args.get("url", "")
    prompt = args.get("prompt", "")
    
    if not url:
        return ToolResult(tool_call_id=tool_call_id, output="URL is required", is_error=True)
    
    if context.abort_signal and context.abort_signal():
        return ToolResult(tool_call_id=tool_call_id, output="Aborted", is_error=True)
    
    try:
        parsed_url = None
        hostname = ""
        try:
            parsed_url = __import__('urllib.parse', fromlist=['url']).urlparse(url)
            hostname = parsed_url.hostname or ""
        except Exception:
            pass
        
        if hostname and is_preapproved_host(hostname):
            pass
        
        import time
        start = time.time()
        
        timeout = httpx.Timeout(FETCH_TIMEOUT, connect=CONNECT_TIMEOUT)
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(
                url,
                headers={
                    'User-Agent': USER_AGENT,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
            )
            
            if not response.is_success:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"HTTP {response.status_code} {response.status_text}",
                    is_error=True,
                )
            
            content_type = response.headers.get('content-type', '')
            text = response.text
            bytes_count = len(text.encode('utf-8'))
            
            if 'application/json' in content_type:
                truncated = text[:MAX_CONTENT_SIZE]
                if len(text) > MAX_CONTENT_SIZE:
                    truncated += '\n...(truncated)'
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=truncated,
                    is_error=False,
                )
            
            if 'html' in content_type.lower():
                text = extract_text(text)
            
            if len(text) > MAX_CONTENT_SIZE:
                text = text[:MAX_CONTENT_SIZE] + '\n...(truncated)'
            
            duration_ms = int((time.time() - start) * 1000)
            
            return ToolResult(
                tool_call_id=tool_call_id,
                output=text,
                is_error=False,
            )
            
    except httpx.TimeoutException:
        return ToolResult(tool_call_id=tool_call_id, output="Fetch error: Timeout after 30 seconds", is_error=True)
    except httpx.RequestError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Fetch error: {str(e)}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Fetch error: {str(e)}", is_error=True)


WebFetchTool = ToolDef(
    name="web_fetch",
    description="Fetch a URL and return its content as text. Useful for reading web pages, APIs, documentation.",
    input_schema=INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_execute,
)


__all__ = ["WebFetchTool", "is_preapproved_host"]