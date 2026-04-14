import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as c:
        r = await c.get('http://localhost:7778/health', timeout=5)
        print("Health check:", r.json())

asyncio.run(test())