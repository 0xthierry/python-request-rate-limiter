import aiohttp
import asyncio
import json

async def fetcher(session, url):
  async with session.get(url) as response:
      print(f"Response status: {response.status}")
      result = await response.text()
      result = json.loads(result)
      return result

async def main():
  url = 'http://127.0.0.1:9000/status'

  async with aiohttp.ClientSession() as session:
    # Prepare to make 15 requests to test the rate limit of 10 requests per minute
    tasks = [fetcher(session, url) for _ in range(15)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())