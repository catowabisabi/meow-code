"""WebSearchTool — search the web for current information."""
import urllib.parse
import re
from typing import Any, Dict, List

import httpx

from .types import ToolDef, ToolResult, ToolContext

MAX_CONTENT_SIZE = 50000
FETCH_TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
USER_AGENT = 'Mozilla/5.0 (compatible; AICodeAssistant/1.0)'


def extract_ddg_results(html: str, limit: int) -> List[Dict[str, str]]:
    results = []
    blocks = html.split('class="result-link"')
    
    for block in blocks[1:limit + 1]:
        href_match = re.search(r'href="([^"]*)"', block)
        text_match = re.search(r'>([^<]+)</a>', block)
        
        if href_match and text_match:
            url = href_match.group(1)
            if 'duckduckgo.com' in url:
                continue
            results.append({
                'title': text_match.group(1).strip(),
                'url': url,
            })
    
    if not results:
        for url, title in re.findall(r'<a[^>]+href="(https?://[^"]*)"[^>]*>([^<]+)</a>', html):
            if len(results) >= limit:
                break
            if 'duckduckgo.com' in url:
                continue
            results.append({'title': title.strip(), 'url': url})
    
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