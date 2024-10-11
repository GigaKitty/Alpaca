from apscheduler.schedulers.asyncio import AsyncIOScheduler
from urllib.parse import urlencode, urlunparse
import asyncio
import json
import logging
import os
import numpy as np
import pandas as pd
import pandas_ta as ta
import pymarketstore as pymkts
import redis.asyncio as aioredis
import requests
import logging

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
hook_url = os.getenv("VOLATILITYVULTURE_ORDER_ENDPOINT")
list_name = "volatilityvulture_list"
channel_name = "stocks_channel"

BASE_URL = (
    "https://data.alpaca.markets/v1beta1/screener/stocks/most-actives?by=volume&top=100"
)
# Set the display options to NO LIMITS!!!
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)

redis_host = os.getenv("REDIS_HOST", "redis-stack")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    socket_timeout=10,  # Increase the timeout value
    connection_pool=aioredis.ConnectionPool(
        host="redis-stack", port=redis_port, max_connections=10
    ),
)

logging.basicConfig(level=logging.INFO)



def build_url(base_url, params):
    query_string = urlencode(params)
    url_parts = list(urlunparse(("", "", base_url, "", query_string, "")))
    return urlunparse(url_parts)


async def get_list(key):
    list_data = await redis.lrange(key, 0, -1)
    if list_data:
        list_data = json.loads(list_data[0].decode("utf-8"))
    return list_data


async def publish_list(list_name, message):
    try:
        await redis.delete(list_name)
        await redis.lpush(list_name, message)
        logging.info(f"Published message: {message} to list: {list_name}")
    except aioredis.exceptions.TimeoutError:
        logging.error(
            f"Timeout error while publishing message: {message} to list: {list_name}"
        )
    except aioredis.exceptions.RedisError as e:
        logging.error(
            f"Redis error while publishing message: {message} to list: {list_name}: {e}"
        )


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


async def send_order(action, stock, data):
    """
    Sends a POST request to the TradingView webhook URL
    required fields: action, comment, low, high, close, volume, interval, signature, ticker, trailing
    side is hardcoded as buy for now
    """
    data = {
        "action": action,
        "close": data["Close"],
        "comment": "macd-rsi-bb-volatilityvulture",
        "high": data["High"],
        "interval": "1m",
        "price": data["Close"],
        "low": data["Low"],
        "open": data["Open"],
        "risk": os.getenv(
            "RISK", 0.001
        ),  # Set a default low so that if it's not set it will be a low value
        "signature": tv_sig,
        "ticker": stock,
        "volume": data["Volume"],
        "postprocess": ["trailing_stop_tiered"],
    }

    # Sending a POST request with JSON data
    response = requests.post(hook_url, json=data)

    if response.status_code == 200:
        try:
            logging.info(f"Order sent successfully for {stock}")
        except requests.exceptions.JSONDecodeError:
            logging.error("Response is not in JSON format.")
    else:
        logging.error(f"HTTP Error encountered: {response}")


async def process_stock(stock):
    """ """
    # get data from marketstore
    result = await read_data_from_marketstore(stock)
    if result is None:
        logging.error(f"No data found for {stock}")
        return
    else:
        if len(result) < 10:  # Assuming length=10 for Supertrend
            logging.error(f"Not enough data to calculate Supertrend for {stock}")
            return

        # Define Supertrend parameters
        length = 10
        multiplier = 3.0

        # Calculate the Supertrend
        result.ta.supertrend(length=length, multiplier=multiplier, append=True)

        # Check if the DataFrame is empty after dropping NaN values
        if result.empty:
            logging.error(
                f"DataFrame is empty after calculating Supertrend for {stock}"
            )
            return

        last_row = result.iloc[-1]

        # Calculate additional indicators (e.g., RSI, MACD)
        result.ta.rsi(append=True)
        result.ta.macd(append=True)

        # Get the last row of additional indicators
        last_row_rsi = result.iloc[-1]["RSI_14"]
        last_row_macd = result.iloc[-1]["MACD_12_26_9"]
        last_row_macd_signal = result.iloc[-1]["MACDs_12_26_9"]

        # Define weights for each indicator
        weight_supertrend = 0.5
        weight_rsi = 0.25
        weight_macd = 0.25

        # Log the calculated values for debugging
        logging.info(f"Supertrend: {last_row['SUPERT_10_3.0']}")
        logging.info(f"RSI: {last_row_rsi}")
        logging.info(f"MACD: {last_row_macd}")
        logging.info(f"MACD Signal: {last_row_macd_signal}")

        # Determine buy or sell signal using weighted indicators
        supertrend_signal = 1 if last_row["SUPERT_10_3.0"] > 0 else -1
        rsi_signal = 1 if last_row_rsi < 30 else -1 if last_row_rsi > 70 else 0
        macd_signal = (
            1
            if last_row_macd > last_row_macd_signal
            else -1 if last_row_macd < last_row_macd_signal else 0
        )

        # Calculate composite score
        composite_score = (
            (weight_supertrend * supertrend_signal)
            + (weight_rsi * rsi_signal)
            + (weight_macd * macd_signal)
        )

        # Determine final signal based on composite score
        if composite_score > 0:
            action = "buy"
            logging.info(f"Buy signal generated for {stock}")
        elif composite_score < 0:
            action = "sell"
            logging.info(f"Sell signal generated for {stock}")
        else:
            action = None
            logging.info(f"No clear signal for {stock}")

        if action:
            await send_order(action, stock, last_row)


async def update_list():
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
        # open_positions = await get_all_positions()
        # omit existing positions and stocks from the earnings and aristocrats list
        omit_list = earnings_list + aristocrats_list
        # Filter the most active stocks
        filtered_stocks = sorted(
            [
                stock["symbol"]
                for stock in most_active_stocks
                if stock["symbol"] not in omit_list
            ]
        )
        await publish_list("volatilityvulture_list", json.dumps(filtered_stocks))
        logging.info(f"Published list: {filtered_stocks} to volatilityvulture_list")

    else:
        logging.error(f"HTTP Error encountered: {response}")


async def monitor_redis_channel():
    volatility = await get_list(list_name)
    print(f"Monitoring channel: {channel_name}")
    print(f"Subscribed to list: {volatility}")
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel_name)

    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                message_data_list = json.loads(message["data"].decode("utf-8"))
            except json.JSONDecodeError:
                logging.error("Invalid JSON received.")
                continue
            
            for message_data in message_data_list:
                symbol = message_data.get("S")
                if symbol in volatility:
                    await process_stock(symbol)

    await redis.close()


async def scheduler_task(scheduler):
    """
    Starts the scheduler to run tasks at specified intervals.
    """
    scheduler.start()
    # Keep the scheduler running indefinitely
    while True:
        await asyncio.sleep(1)


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_list,
        "cron",
        day_of_week="mon-fri",
        hour="9-20",
        minute="*/5",  # Every 5 minutes
        timezone="America/New_York",
    )

    await asyncio.gather(
        monitor_redis_channel(),
        scheduler_task(scheduler),
    )


if __name__ == "__main__":
    asyncio.run(main())
