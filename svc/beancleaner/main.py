from alpaca.trading.client import TradingClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import asyncio
import logging
import os
import redis.asyncio as aioredis

#######################################################
#### ENVIRONMENT SETUP ################################
#######################################################
"""
 Set the environment variable ENVIRONMENT to main or dev
"""
paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

"""
Initialize the Alpaca API
If it's dev i.e. paper trading then it uses the paper trading API
"""
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Set the timezone to EST
est = timezone("US/Eastern")

# Configure logging
logging.basicConfig(level=logging.INFO)
#######################################################
#######################################################
#######################################################


def clean_the_bean():
    """
    The overall idea is to free up capital and don't carry trades through after hours or weekends.
    Tickers can be fitlered based on a list of tickers that are known to have earnings or other events that we'd like to hodl.
    @TODO: add a check to see if it's on a global list for instance earnings and if it is then skip it. This data can be set/get from redis as it's not critical for persistance
    """
    print("Cleaning the bean")
    # Get all open positions
    positions = api.get_all_positions()

    for position in positions:
        symbol = position.symbol
        unrealized_pl = float(position.unrealized_pl)

        # Check if the unrealized loss is less than $1
        if unrealized_pl >= -1.0:
            try:
                # Close the position
                api.close_position(symbol)
                if unrealized_pl >= 0:
                    print(
                        f"Closed position in {symbol} with a profit of {unrealized_pl}"
                    )
                else:
                    print(f"Closed position in {symbol} with a loss of {unrealized_pl}")
            except Exception as e:
                print(f"Error closing position in {symbol}: {e}")


async def scheduler_task(scheduler):
    """
    Starts the scheduler to run tasks at specified intervals.
    """
    scheduler.start()
    # Keep the scheduler running indefinitely
    logging.info("Scheduler started")
    while True:
        await asyncio.sleep(1)


async def main():
    scheduler = AsyncIOScheduler(timezone=est)
    logging.info("Starting the bean cleaner service")
    trigger = CronTrigger(day_of_week="mon-fri", hour=15, minute=55, timezone=est)
    logging.info(f"Bean cleaner scheduled to run at {trigger}")
    scheduler.add_job(clean_the_bean, trigger)
    await scheduler_task(scheduler)


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())
