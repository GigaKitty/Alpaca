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

# Redis connection details
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
#######################################################
#######################################################
#######################################################


async def get_list(list_name):
    """
    List is published via another service and is part of earnyearn service
    This grabs the list from Redis returns the list of tickers and closes redis connection
    """
    redis = None
    try:
        redis = aioredis.from_url(
            f"redis://{redis_host}:{redis_port}",
            encoding="utf-8",
            db=0,
            decode_responses=True,
            socket_timeout=60,
            socket_connect_timeout=60,
            socket_keepalive=True,
        )
        latest_message = await redis.lindex(list_name, 0)
        return latest_message
    except Exception as e:
        logging.error(f"Error fetching latest message from Redis: {e}")
        return None
    finally:
        if redis:
            await redis.aclose()


async def clean_the_bean():
    """
    The overall idea is to free up capital and don't carry trades through after hours or weekends.
    Tickers are filtered based on a list of tickers that are known to have earnings or other events that we'd like to hold.
    Currently only supports teh earnyearn list but others can be added if needed such as positions we'd like to hold over time.
    """
    logging.info("fetching positions to clean up the beans")
    positions = api.get_all_positions()
    logging.info(f"Found {len(positions)} positions")

    # @TODO: make this dynamically populated from skip_list in redis
    earnings_list = await get_list('earnings_list')
    aristocrats_list = await get_list('dividend_aristocrats')
    # merge the lists
    skip_list = earnings_list + aristocrats_list
    logging.info(f"Found {len(skip_list)} earnings")
    
    # us_equity only keep stocks and omit options
    remaining_positions = [
        position for position in positions if position.symbol not in skip_list and position.asset_class == "us_equity"
    ]

    for position in remaining_positions:
        symbol = position.symbol
        unrealized_pl = float(position.unrealized_pl)
        logging.info(
            f"Found position in {position.symbol} with unrealized P/L {unrealized_pl}"
        )

        # Check if the unrealized loss is greater than -$1
        if unrealized_pl >= -1:
            try:
                logging.info(f"Closing position in {symbol} with unrealized P/L")
                api.close_position(symbol)
                if unrealized_pl >= 0:
                    logging.info(
                        f"Closing position in {symbol} with a profit of {unrealized_pl}"
                    )
                else:
                    logging.info(
                        f"Closed position in {symbol} with a loss of {unrealized_pl}"
                    )
            except Exception as e:
                logging.error(f"Error closing position in {symbol}: {e}")


async def scheduler_task(scheduler):
    """
    Starts the scheduler to run tasks at specified intervals.
    """
    scheduler.start()
    logging.info(f"Scheduler started")
    while True:
        await asyncio.sleep(1)


async def main():
    """
    Primary entry point for the application sets up the scheduler to run the bean cleaner service
    """
    scheduler = AsyncIOScheduler(timezone=est)
    logging.info("Starting the bean cleaner service")
    trigger = CronTrigger(day_of_week="mon-fri", hour=15, minute=59, timezone=est)
    logging.info(f"Bean cleaner scheduled to run at {trigger}")
    scheduler.add_job(clean_the_bean, trigger)
    await scheduler_task(scheduler)


if __name__ == "__main__":
    """
    Initialize the bean cleaner service
    """
    async def run_tasks():
        await main()

    asyncio.run(run_tasks())
