"""WebSearchTool — search the web for current information."""
import urllib.parse
import re
from typing import Any, Dict, List

import httpx

from .types import ToolDef, ToolResult, ToolContext

MAX_CONTENT_SIZE = 50000
FETCH_TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def _resolve_ddg_url(raw_url: str) -> str:
    """Extract the real URL from a DDG redirect like //duckduckgo.com/l/?uddg=ENCODED_URL."""
    if 'uddg=' in raw_url:
        m = re.search(r'uddg=([^&]+)', raw_url)
        if m:
            return urllib.parse.unquote(m.group(1))
    if raw_url.startswith('//'):
        return 'https:' + raw_url
    return raw_url


def extract_ddg_results(html: str, limit: int) -> List[Dict[str, str]]:
    results = []

    # DDG Lite: <a href="//duckduckgo.com/l/?uddg=REAL_URL" class='result-link'>Title</a>
    for m in re.finditer(
        r"<a\s+[^>]*?href=['\"]([^'\"]+)['\"][^>]*?class=['\"]result-link['\"][^>]*>([^<]+)</a>"
        r"|<a\s+[^>]*?class=['\"]result-link['\"][^>]*?href=['\"]([^'\"]+)['\"][^>]*>([^<]+)</a>",
        html,
    ):
        raw_url = m.group(1) or m.group(3) or ''
        title = m.group(2) or m.group(4) or ''
        if not raw_url:
            continue
        url = _resolve_ddg_url(raw_url)
        if 'duckduckgo.com' in url:
            continue
        # Extract snippet from the next result-snippet cell
        snippet = ''
        pos = m.end()
        snip_match = re.search(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", html[pos:pos + 500], re.DOTALL)
        if snip_match:
            snippet = re.sub(r'<[^>]+>', '', snip_match.group(1)).strip()
        results.append({'title': title.strip(), 'url': url, 'snippet': snippet})
        if len(results) >= limit:
            break

    return results


INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "The search query to use", "minLength": 2},
        "allowed_domains": {"type": "array", "items": {"type": "string"}, "description": "Only include search results from these domains"},
        "blocked_domains": {"type": "array", "items": {"type": "string"}, "description": "Never include search results from these domains"},
    },
    "required": ["query"],
}


async def _execute(args: Dict[str, Any], context: ToolContext) -> ToolResult:
    tool_call_id = getattr(context, 'tool_call_id', '') or ""
    query = args.get("query", "")
    
    if not query:
        return ToolResult(tool_call_id=tool_call_id, output="Query is required", is_error=True)
    
    if context.abort_signal and context.abort_signal():
        return ToolResult(tool_call_id=tool_call_id, output="Aborted", is_error=True)
    
    allowed = args.get("allowed_domains")
    blocked = args.get("blocked_domains")
    if allowed and blocked:
        return ToolResult(tool_call_id=tool_call_id, output="Cannot specify both allowed_domains and blocked_domains", is_error=True)
    
    import time
    start_time = time.time()
    
    timeout = httpx.Timeout(FETCH_TIMEOUT, connect=CONNECT_TIMEOUT)
    search_url = f'https://lite.duckduckgo.com/lite/?q={urllib.parse.quote_plus(query)}'
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(search_url, headers={'User-Agent': USER_AGENT})
            
            if not response.is_success:
                return ToolResult(
                    tool_call_id=tool_call_id,
                    output=f"Search failed: HTTP {response.status_code}",
                    is_error=True,
                )
            
            results = extract_ddg_results(response.text, 8)
            duration = time.time() - start_time
            
            if not results:
                return ToolResult(
                tool_call_id=tool_call_id,
                output=f"Web search results for query: \"{query}\"\n\nNo results found.",
                is_error=False,
            )
            
            formatted_lines = [f"Web search results for query: \"{query}\"\n"]
            for r in results:
                formatted_lines.append(f"Links: {r['title']} - {r['url']}")
            formatted_lines.append("\nREMINDER: You MUST include the sources above in your response to the user using markdown hyperlinks.")
            
            formatted_output = "\n".join(formatted_lines)
            
            return ToolResult(
                tool_call_id=tool_call_id,
                output=formatted_output,
                is_error=False,
            )
            
    except httpx.TimeoutException:
        return ToolResult(tool_call_id=tool_call_id, output="Search error: Timeout after 30 seconds", is_error=True)
    except httpx.RequestError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Search error: {str(e)}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Search error: {str(e)}", is_error=True)


WebSearchTool = ToolDef(
    name="web_search",
    description="Search the web and return results. Uses DuckDuckGo Lite (no API key needed).",
    input_schema=INPUT_SCHEMA,
    is_read_only=True,
    risk_level="low",
    execute=_execute,
)


__all__ = ["WebSearchTool"]