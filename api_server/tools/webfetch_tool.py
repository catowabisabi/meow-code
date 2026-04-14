"""WebFetch tool with security - bridging gap with TypeScript WebFetchTool"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re
import urllib.parse


logger = logging.getLogger(__name__)


PREAPPROVED_DOMAINS = {
    "github.com", "api.github.com",
    "gitlab.com", "api.gitlab.com",
    "stackoverflow.com", "*.stackoverflow.com",
    "npmjs.com", "registry.npmjs.org",
    "pypi.org", "files.pythonhosted.org",
    "crates.io", "doc.rust-lang.org",
    "golang.org", "pkg.go.dev",
    "npmjs.com", "yarnpkg.com",
    "docker.io", "hub.docker.com",
    "kubernetes.io", "k8s.io",
    "terraform.io", "registry.terraform.io",
    "aws.amazon.com", "*.amazonaws.com",
    "cloud.google.com", "console.cloud.google.com",
    "azure.microsoft.com", "portal.azure.com",
    "heroku.com", "api.heroku.com",
    "vercel.com", "*.vercel.app",
    "netlify.com", "*.netlify.app",
    "cloudflare.com", "dash.cloudflare.com",
    "digitalocean.com", "api.digitalocean.com",
    "stripe.com", "dashboard.stripe.com",
    "sendgrid.com", "*.sendgrid.com",
    "mailgun.com", "*.mailgun.com",
    "anthropic.com", "api.anthropic.com",
    "openai.com", "api.openai.com",
    "google.com", "*.google.com",
    "microsoft.com", "*.microsoft.com",
    "apple.com", "*.apple.com",
    "facebook.com", "*.facebook.com",
    "twitter.com", "x.com",
    "linkedin.com", "*.linkedin.com",
    "reddit.com", "*.reddit.com",
    "medium.com", "*.medium.com",
    "dev.to", "*.dev.to",
    "hashnode.com", "*.hashnode.com",
    "stackoverflow.com", "*.stackoverflow.com",
    "superuser.com", "*.superuser.com",
    "serverfault.com", "*.serverfault.com",
    "askubuntu.com", "*.askubuntu.com",
}


MAX_REDIRECTS = 5
MAX_RESPONSE_SIZE = 10 * 1024 * 1024
REQUEST_TIMEOUT = 30


@dataclass
class WebFetchResult:
    content: str
    status_code: int
    headers: Dict[str, str]
    url: str
    is_truncated: bool = False
    error: Optional[str] = None


def is_url_preapproved(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    
    if domain in PREAPPROVED_DOMAINS:
        return True
    
    for approved in PREAPPROVED_DOMAINS:
        if approved.startswith("*."):
            base = approved[2:]
            if domain.endswith(base) or domain == base:
                return True
    
    return False


def validate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    
    if not parsed.scheme:
        return False
    
    if parsed.scheme not in ("http", "https"):
        return False
    
    if not parsed.netloc:
        return False
    
    dangerous_patterns = [
        r"javascript:",
        r"data:text/html",
        r"file://",
        r"ftp://",
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    
    return True


async def fetch_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    allow_redirects: bool = True,
    timeout: float = REQUEST_TIMEOUT
) -> WebFetchResult:
    if not validate_url(url):
        return WebFetchResult(
            content="",
            status_code=0,
            headers={},
            url=url,
            error="Invalid URL"
        )
    
    redirect_count = 0
    current_url = url
    
    async with asyncio.timeout(timeout):
        while redirect_count < MAX_REDIRECTS:
            if not is_url_preapproved(current_url):
                return WebFetchResult(
                    content="",
                    status_code=0,
                    headers={},
                    url=current_url,
                    error=f"URL not in preapproved list: {urllib.parse.urlparse(current_url).netloc}"
                )
            
            try:
                result = await _do_fetch(current_url, method, headers, body)
                
                if result.status_code in (301, 302, 303, 307, 308) and allow_redirects:
                    redirect_count += 1
                    location = result.headers.get("location", result.headers.get("Location", ""))
                    if location:
                        if location.startswith("/"):
                            parsed = urllib.parse.urlparse(current_url)
                            current_url = f"{parsed.scheme}://{parsed.netloc}{location}"
                        else:
                            current_url = location
                        continue
                
                return result
                
            except asyncio.TimeoutError:
                return WebFetchResult(
                    content="",
                    status_code=0,
                    headers={},
                    url=current_url,
                    error="Request timed out"
                )
            except Exception as e:
                return WebFetchResult(
                    content="",
                    status_code=0,
                    headers={},
                    url=current_url,
                    error=str(e)
                )
        
        return WebFetchResult(
            content="",
            status_code=0,
            headers={},
            url=current_url,
            error="Too many redirects"
        )


async def _do_fetch(
    url: str,
    method: str,
    headers: Optional[Dict[str, str]],
    body: Optional[str]
) -> WebFetchResult:
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method,
            url,
            headers=headers,
            data=body,
            allow_redirects=False,
            max_response_size=MAX_RESPONSE_SIZE
        ) as response:
            content = await response.text()
            
            return WebFetchResult(
                content=content[:MAX_RESPONSE_SIZE],
                status_code=response.status,
                headers=dict(response.headers),
                url=str(response.url),
                is_truncated=len(content) >= MAX_RESPONSE_SIZE
            )


class WebFetchTool:
    name = "webfetch"
    description = "Fetch content from URLs"
    
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "HEAD"],
                "description": "HTTP method",
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "description": "Additional headers"
            },
            "body": {
                "type": "string",
                "description": "Request body"
            }
        },
        "required": ["url"]
    }
