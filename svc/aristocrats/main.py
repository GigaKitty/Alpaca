from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import os
import pandas as pd
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


async def store_in_redis(data):
    """
    Stores the dividend aristocrats list in Redis so other services can consume it
    """
    await redis.set("dividend_aristocrats", pd.DataFrame(data).to_json())
    await redis.aclose()


async def main():
    aristocrats = await scrape_dividend_aristocrats()
    await store_in_redis(aristocrats)


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
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run_scheduler()
