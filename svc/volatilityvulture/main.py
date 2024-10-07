from alpaca.trading.client import TradingClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import os
import redis
import redis.asyncio as aioredis
import requests
import asyncio
import datetime
import json
import logging
import numpy as np
import os
import pandas as pd
import pandas_ta as ta
import pymarketstore as pymkts
import random
from urllib.parse import urlencode, urlunparse


"""
This service monitors the most active stocks and determines the trading strategy based on the volatility of the stock.
It creates a list of those volatile stocks and sends it to a redis websocket stream so that it can subscribe back to that list for price updates.
It also stores the market data in Marketstore for further analysis.
When an updated message comes from redis it will calculate the trading strategy and send a TradingView webhook with the trading signal if one occurs
This particular strategy uses Supertrend
"""

environment = os.getenv("ENVIRONMENT", "dev")
paper = True if environment != "main" else False
marketstore_client = pymkts.Client(f"http://marketstore:5993/rpc")
tv_sig = os.getenv("TRADINGVIEW_SECRET")

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

BASE_URL = (
    "https://data.alpaca.markets/v1beta1/screener/stocks/most-actives?by=volume&top=100"
)

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_conn = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    socket_timeout=10,  # Increase the timeout value
    connection_pool=aioredis.ConnectionPool(
        host="redis-stack", port=redis_port, max_connections=10
    ),
)


async def redis_listener():
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("stocks_channel")

    async for message in pubsub.listen():
        if message["type"] == "message":
            await process_message(redis, message["data"])


def build_url(base_url, params):
    query_string = urlencode(params)
    url_parts = list(urlunparse(("", "", base_url, "", query_string, "")))
    return urlunparse(url_parts)


async def get_list(key):
    list_data = await redis_conn.lrange(key, 0, -1)
    if list_data:
        list_data = json.loads(list_data[0].decode("utf-8"))
    return list_data


async def publish_list(list_name, message):
    try:
        await redis_conn.delete(list_name)
        await redis_conn.lpush(list_name, message)
        # print(f"Published message: {message} to list: {list_name}")
    except aioredis.exceptions.TimeoutError:
        print(f"Timeout error while publishing message: {message} to list: {list_name}")
    except aioredis.exceptions.RedisError as e:
        print(
            f"Redis error: {e} while publishing message: {message} to list: {list_name}"
        )


async def get_all_positions():
    positions = api.get_all_positions()
    return [position.symbol for position in positions]


async def process_stock(stock):
    """
    we want to get
    """
    # sleep for random seconds to simulate processing time in a range
    print(f"Processing stock: {stock}")
    # get data from marketstore
    result = await read_data_from_marketstore(stock)
    if result is None:
        print(f"Error getting data for {stock}")
        return
    else:
        print(f"Got data for {stock}")


async def read_data_from_marketstore(symbol):
    # Define the query parameters
    timeframe = "1Min"
    attribute_group = "OHLCV"

    params = pymkts.Params(
        symbols=symbol, timeframe=timeframe, attrgroup=attribute_group
    )

    # Perform the query
    try:
        logging.info(f"Querying data for {symbol}/{timeframe}/{attribute_group}")
        response = marketstore_client.query(params).first()
        if response is None:
            logging.error("Marketstore query returned no results.")
            return None

        df = response.df()
        if df is None or df.empty:
            logging.error("DataFrame is empty or None.")
            return None

        return df
    except Exception as e:
        logging.error(f"Error querying Marketstore: {e}")
        return None


async def main():
    headers = {
        "APCA-API-KEY-ID": os.getenv("APCA_API_KEY_ID"),
        "APCA-API-SECRET-KEY": os.getenv("APCA_API_SECRET_KEY"),
    }

    response = requests.get(BASE_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        most_active_stocks = data.get("most_actives", [])
        most_active_stocks = most_active_stocks[
            :100
        ]  # Get the top 100 most active stocks
        earnings_list = await get_list("earnings_list")
        aristocrats_list = await get_list("dividend_aristocrats")
        open_positions = await get_all_positions()
        # omit existing positions and stocks from the earnings and aristocrats list
        omit_list = earnings_list + aristocrats_list + open_positions

        # Filter the most active stocks
        filtered_stocks = sorted(
            [
                stock["symbol"]
                for stock in most_active_stocks
                if stock["symbol"] not in omit_list
            ]
        )

        await publish_list("volatilityvulture_list", json.dumps(filtered_stocks))
        print(f"Published the list of volatile stocks: {filtered_stocks}")

    else:
        print(f"Error: {response.status_code} - {response.text}")


def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main,
        "cron",
        day_of_week="mon-fri",
        hour="9-20",
        minute="*/5",  # Every 5 minutes
        timezone="America/New_York",
    )
    scheduler.start()
    print("Scheduler started")
    try:
        loop = asyncio.get_event_loop()
        if os.getenv("DEBUG", False):
            loop.run_until_complete(main())

        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run_scheduler()
