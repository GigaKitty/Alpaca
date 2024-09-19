from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import json
import os
import redis.asyncio as aioredis

#######################################################
#### ENVIRONMENT SETUP ################################
#######################################################
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/S%26P_500_Dividend_Aristocrats"
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

redis = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    socket_timeout=10,  # Increase the timeout value
    connection_pool=aioredis.ConnectionPool(
        host=redis_host, port=redis_port, max_connections=10
    ),
)
#######################################################
#######################################################
#######################################################
async def scrape_dividend_aristocrats():
    """
    Scrapes  wikipedia for the dividend aristocrats and returns a list of ticker symbols
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(WIKIPEDIA_URL) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", {"class": "wikitable sortable"})
            rows = table.find_all("tr")
            aristocrats = []
            for row in rows[1:]:
                cols = row.find_all("td")
                ticker_symbol = cols[1].text.strip()
                aristocrats.append(ticker_symbol)
                print(f"Added {ticker_symbol} to the list")
            print(aristocrats)
            return aristocrats


async def publish_list(list_name, message):
    try:
        await redis.delete(list_name)
        await redis.lpush(list_name, message)
        print(f"Published message: {message} to list: {list_name}")
    except aioredis.exceptions.TimeoutError:
        print(f"Timeout error while publishing message: {message} to list: {list_name}")
    except aioredis.exceptions.RedisError as e:
        print(
            f"Redis error: {e} while publishing message: {message} to list: {list_name}"
        )


async def main():
    aristocrats = await scrape_dividend_aristocrats()
    await publish_list("dividend_aristocrats", json.dumps(aristocrats))


def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main,
        "cron",
        day_of_week="mon-fri",
        hour=16,
        minute=20,
        timezone="America/New_York",
    )
    scheduler.start()
    print("Scheduler started")
    # Run once on startup
    asyncio.get_event_loop().run_until_complete(main())
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run_scheduler()
