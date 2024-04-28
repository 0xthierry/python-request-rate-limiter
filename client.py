import aiohttp
import asyncio
import time
import random
from pyrate_limiter import Duration, Rate, Limiter, BucketFullException

rate = Rate(10, Duration.MINUTE)
limiter = Limiter(rate, raise_when_fail=False)

async def retry(status_code, retries, retry_after):
    if status_code == 429 and retries > 0:
        retry_delay = min(2 ** (5 - retries) * 10, int(retry_after))
        print(f"Rate limit hit. Retrying after {retry_delay} seconds...")
        await asyncio.sleep(retry_delay)
        return True
    return False

def bucket_retry_after(name, weight):
    bucket = limiter.bucket_factory.get(name)
    rate_item = limiter.bucket_factory.wrap_item(name, weight)
    retry_after = bucket.waiting(rate_item) / 1000
    jitter = random.uniform(0, retry_after * 0.3)
    return max(int(retry_after + jitter), int(retry_after))

async def fetcher(session: aiohttp.ClientSession, url, retries=5):
    try:
        is_acquired = limiter.try_acquire(url, 1)

        if not is_acquired:
            if retries > 0:
              retry_delay = bucket_retry_after(url, 1)
              print(f"Rate limit hit. Retrying after {retry_delay} seconds...")
              await asyncio.sleep(retry_delay)
              return await fetcher(session, url, retries - 1)
            else:
              raise Exception("Rate limit hit. No retries left.")

        async with session.get(url) as response:
            data = await response.json()
            if await retry(response.status, retries, response.headers.get('Retry-After', bucket_retry_after(url, 1))):
                return await fetcher(session, url, retries - 1)
            return data
    except aiohttp.ClientResponseError as e:
        if await retry(e.status, retries, e.headers.get('Retry-After', bucket_retry_after(url, 1))):
            return await fetcher(session, url, retries - 1)
        raise
    except aiohttp.ClientError as e:
        print(f"Network-related error occurred: {e}")
        if retries > 0:
            await asyncio.sleep(5)  # Fixed short delay before retrying
            return await fetcher(session, url, retries - 1)
        raise

async def main():
    url = 'http://127.0.0.1:9000/status'
    async with aiohttp.ClientSession() as session:
        tasks = [fetcher(session, url) for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print("Error:", result)
            else:
                print("Response:", result)

if __name__ == "__main__":
    # Record the start time using time.perf_counter() for high resolution timing
    start_time = time.perf_counter()

    # Run the main coroutine and manage the event loop
    asyncio.run(main())

    # Record the end time
    end_time = time.perf_counter()

    # Calculate the duration in seconds
    duration_seconds = end_time - start_time

    # Optionally convert duration to minutes
    duration_minutes = duration_seconds / 60

    print(f"Execution took {duration_seconds:.2f} seconds")
    print(f"Execution took {duration_minutes:.2f} minutes")
