import httpx, asyncio, re

async def test():
    query = "Toronto public library branches number 2024"
    url = f'https://lite.duckduckgo.com/lite/?q={query.replace(" ", "+")}'
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
        r = await c.get(url, headers={'User-Agent': ua})
        print(f'Status: {r.status_code}')
        print(f'Final URL: {r.url}')
        print(f'HTML length: {len(r.text)}')

        # Check for result-link
        links = re.findall(r'result-link', r.text)
        print(f'\nFound "result-link" occurrences: {len(links)}')

        # Check for any <a> tags
        a_tags = re.findall(r'<a\s[^>]*href=[^>]+>', r.text[:5000])
        print(f'\n<a> tags in first 5000 chars: {len(a_tags)}')
        for t in a_tags[:10]:
            print(f'  {t}')

        # Show raw HTML around any result areas
        for pattern in ['result-link', 'result__a', 'result__url', 'web-result', 'results_links']:
            idx = r.text.find(pattern)
            if idx >= 0:
                print(f'\n--- Found "{pattern}" at pos {idx} ---')
                print(r.text[max(0,idx-200):idx+300])

        # Test the EXACT regex from web_search.py
        print('\n=== Testing EXACT regex from web_search.py ===')
        pattern1 = r"<a\s+[^>]*?href=['\"]([^'\"]+)['\"][^>]*?class=['\"]result-link['\"][^>]*>([^<]+)</a>"
        pattern2 = r"<a\s+[^>]*?class=['\"]result-link['\"][^>]*?href=['\"]([^'\"]+)['\"][^>]*>([^<]+)</a>"
        
        matches1 = list(re.finditer(pattern1, r.text))
        matches2 = list(re.finditer(pattern2, r.text))
        print(f'Pattern 1 (href first) matches: {len(matches1)}')
        print(f'Pattern 2 (class first) matches: {len(matches2)}')
        
        if matches1:
            m = matches1[0]
            print(f'Pattern 1 sample: href={m.group(1)[:60]}, title={m.group(2)[:40]}')
        if matches2:
            m = matches2[0]
            print(f'Pattern 2 sample: href={m.group(1)[:60]}, title={m.group(2)[:40]}')

        # If no results found, show the full HTML (first 5000 chars)
        if not links:
            print('\n--- FULL HTML (first 5000) ---')
            print(r.text[:5000])

asyncio.run(test())
