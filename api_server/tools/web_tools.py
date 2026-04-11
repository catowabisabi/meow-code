"""
Web tools — fetch URLs and search the web.
"""
import html
import re
import urllib.parse
from typing import Any, Dict

import httpx

from .types import ToolDef, ToolContext, ToolResult

MAX_CONTENT_SIZE = 50000
FETCH_TIMEOUT = 30.0
CONNECT_TIMEOUT = 10.0
USER_AGENT = 'Mozilla/5.0 (compatible; AICodeAssistant/1.0)'


def extract_text(html_content: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_ddg_results(html: str, limit: int) -> list:
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
                'snippet': '',
            })
    
    if not results:
        for url, title in re.findall(r'<a[^>]+href="(https?://[^"]*)"[^>]*>([^<]+)</a>', html):
            if len(results) >= limit:
                break
            if 'duckduckgo.com' in url:
                continue
            results.append({'title': title.strip(), 'url': url, 'snippet': ''})
    
    return results


async def web_fetch_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '')
    url = args.get('url', '')
    raw = args.get('raw', False)

    if not url:
        return ToolResult(tool_call_id=tool_call_id, output="URL is required", is_error=True)

    if ctx.abort_signal and ctx.abort_signal():
        return ToolResult(tool_call_id=tool_call_id, output="Aborted", is_error=True)

    timeout = httpx.Timeout(FETCH_TIMEOUT, connect=CONNECT_TIMEOUT)

    try:
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

            if 'application/json' in content_type:
                truncated = text[:MAX_CONTENT_SIZE]
                if len(text) > MAX_CONTENT_SIZE:
                    truncated += '\n...(truncated)'
                return ToolResult(tool_call_id=tool_call_id, output=truncated, is_error=False)

            if not raw and 'html' in content_type.lower():
                text = extract_text(text)

            if len(text) > MAX_CONTENT_SIZE:
                text = text[:MAX_CONTENT_SIZE] + '\n...(truncated)'

            return ToolResult(tool_call_id=tool_call_id, output=text, is_error=False)

    except httpx.TimeoutException:
        return ToolResult(tool_call_id=tool_call_id, output="Fetch error: Timeout after 30 seconds", is_error=True)
    except httpx.RequestError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Fetch error: {str(e)}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Fetch error: {str(e)}", is_error=True)


web_fetch_tool = ToolDef(
    name='web_fetch',
    description='Fetch a URL and return its content as text/markdown. Useful for reading web pages, APIs, documentation.',
    input_schema={
        'type': 'object',
        'required': ['url'],
        'properties': {
            'url': {'type': 'string', 'description': 'URL to fetch'},
            'raw': {'type': 'boolean', 'description': 'Return raw HTML instead of extracted text (default: false)'},
        },
    },
    is_read_only=True,
    risk_level='low',
    execute=web_fetch_execute,
)


async def web_search_execute(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool_call_id = getattr(ctx, 'tool_call_id', '')
    query = args.get('query', '')
    max_results = args.get('max_results', 8)

    if not query:
        return ToolResult(tool_call_id=tool_call_id, output="Query is required", is_error=True)

    if ctx.abort_signal and ctx.abort_signal():
        return ToolResult(tool_call_id=tool_call_id, output="Aborted", is_error=True)

    abort_event = getattr(ctx, 'abort_event', None)
    if abort_event and abort_event.is_set():
        return ToolResult(tool_call_id=tool_call_id, output="Aborted", is_error=True)

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

            results = extract_ddg_results(response.text, max_results)

            if not results:
                return ToolResult(tool_call_id=tool_call_id, output="No search results found.", is_error=False)

            formatted = []
            for i, r in enumerate(results):
                entry = f"{i + 1}. {r['title']}\n   {r['url']}"
                if r.get('snippet'):
                    entry += f"\n   {r['snippet']}"
                formatted.append(entry)

            return ToolResult(tool_call_id=tool_call_id, output='\n\n'.join(formatted), is_error=False)

    except httpx.TimeoutException:
        return ToolResult(tool_call_id=tool_call_id, output="Search error: Timeout after 30 seconds", is_error=True)
    except httpx.RequestError as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Search error: {str(e)}", is_error=True)
    except Exception as e:
        return ToolResult(tool_call_id=tool_call_id, output=f"Search error: {str(e)}", is_error=True)


web_search_tool = ToolDef(
    name='web_search',
    description='Search the web and return results. Uses DuckDuckGo Lite (no API key needed).',
    input_schema={
        'type': 'object',
        'required': ['query'],
        'properties': {
            'query': {'type': 'string', 'description': 'Search query'},
            'max_results': {'type': 'number', 'description': 'Max results to return (default: 8)'},
        },
    },
    is_read_only=True,
    risk_level='low',
    execute=web_search_execute,
)


def register_web_tools() -> None:
    from .executor import register_tool
    register_tool(web_fetch_tool)
    register_tool(web_search_tool)
