import asyncio
import datetime
import finnhub
import json
import logging
import numpy as np
import os
import pandas as pd
import pandas_ta as ta
import pymarketstore as pymkts
import random

import redis
import redis.asyncio as aioredis
import requests

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from apscheduler.schedulers.asyncio import AsyncIOScheduler

########################################
### SETUP ENV
########################################
bar_number = 42
dataframes = {}
fetch_pause = 60
hook_url = os.getenv("EARNYEARN_ORDER_ENDPOINT")
earnings = []
timeframe = "1Min"
attribute_group = "OHLCV"
tv_sig = os.getenv("TRADINGVIEW_SECRET")
list_name = "earnings_list"

client = StockHistoricalDataClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
)

trend_cache = {}

# Set the display options to NO LIMITS!!!
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)


r = redis.Redis(host="redis-stack-core", port=6379)

# Redis connection details
redis_host = os.getenv("REDIS_HOST", "redis-stack")
redis_port = 6379
redis = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    socket_timeout=10,  # Increase the timeout value
    connection_pool=aioredis.ConnectionPool(
        host="redis-stack", port=redis_port, max_connections=10
    ),
)

marketstore_client = pymkts.Client(f"http://marketstore:5993/rpc")
finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

logging.basicConfig(level=logging.INFO)

# Track the last buy timestamp for each symbol
last_buy_timestamp = {}
cooldown_period = 25  # Number of bars to wait before allowing another buy
########################################
########################################

# @TODO: further this by looking at the overall trend of past earnings as well as this period upcoming to determine overall direction.
async def publish_list(list_name, message):
    try:
        await redis.delete(list_name)
        await redis.lpush(list_name, message)
        logging.info(f"Published message: {message} to list: {list_name}")
    except aioredis.exceptions.TimeoutError:
        logging.error(f"Timeout error while publishing message: {message} to list: {list_name}")
    except aioredis.exceptions.RedisError as e:
        logging.error(f"Redis error: {e} while publishing message: {message} to list: {list_name}")

async def trend_getter(symbol):
    try:
        cached_data = await redis.get(f"{symbol}_trend")
        if cached_data:
            return json.loads(cached_data)

        data = finnhub_client.recommendation_trends(symbol)
        sorted_data = sorted(
            data,
            key=lambda x: datetime.datetime.strptime(x["period"], "%Y-%m-%d"),
            reverse=True,
        )
    except Exception as e:
        logging.error(f"Error fetching trend data for {symbol}: {e}")
        return None

    latest_entry = sorted_data[0]

    trends = {
        key: latest_entry[key]
        for key in ["buy", "hold", "sell", "strongBuy", "strongSell"]
    }
    highest_trend = max(trends, key=trends.get)

    logging.info(f"Symbol: {symbol} has the following trends: {trends}")

    # This is weird but prevents all from expiring at the same time.
    expiration_time = random.randint(3600, 7200)

    await redis.set(f"{symbol}_trend", json.dumps(highest_trend), ex=expiration_time)
    logging.info(f"Setting {symbol} with {highest_trend} signal to the earnings list.")

    return highest_trend


async def fetch_earnings_calendar():
    """
    Fetches the earnings calendar for the next 7 days from Finnhub API
    List of symbols is stored in the earnings global variable
    Updates the earnings list with the latest earnings data
    @SEE: https://finnhub.io/docs/api/earnings-calendar
    """
    global earnings

    # reset earnings to empty list
    earnings = []

    # Define the date range for the earnings calendar
    # For example, the next 7 days from today
    start_date = datetime.datetime.now().date()
    end_date = (
        datetime.datetime.now()
        + datetime.timedelta(days=int(os.getenv("FINNHUB_DAYS", 7)))
    ).date()

    # Fetch the earnings calendar
    earnings_calendar = finnhub_client.earnings_calendar(
        _from=start_date.strftime("%Y-%m-%d"),
        to=end_date.strftime("%Y-%m-%d"),
        symbol="",
        international=False,
    )

    #@TODO: maybe remove or improve because now we're shorting enabled so we can be on either side.
    if "earningsCalendar" in earnings_calendar:
        for earning in earnings_calendar["earningsCalendar"]:
            if (
                earning["year"] == datetime.datetime.now().year  # This year
                and earning["epsEstimate"] is not None
                and earning["epsEstimate"] >= 0
                and earning["revenueEstimate"] is not None
                and earning["revenueEstimate"] >= 2.5e8
            ):  # Filter out low volume stocks 2.5e8 is basically 250million in revenue
                trend = await trend_getter(earning["symbol"])
                if trend == "strongBuy" or trend == "buy":
                    # if trend == "strongBuy" or trend == "buy":
                    earnings.append(earning["symbol"])

    else:
        logging.error("😭 No earnings data found for the specified date range.")   

    logging.info(f"📊 {len(earnings)} symbols added to the earnings list. 📊")
    await publish_list(list_name, json.dumps(earnings))


def send_order(action, symbol, data):
    """
    Sends a POST request to the TradingView webhook URL
    required fields: action, comment, low, high, close, volume, interval, signature, ticker, trailing
    side is hardcoded as buy for now
    """
    data = {
        "action": action,
        "close": data["Close"].iloc[-1],
        "comment": "macd-rsi-bb-earnyearn",
        "high": data["High"].iloc[-1],
        "interval": "1m",
        "price": data["Close"].iloc[-1],
        "low": data["Low"].iloc[-1],
        "open": data["Open"].iloc[-1],
        "risk": os.getenv("RISK", 0.001),
        "signature": tv_sig,
        "ticker": symbol,
        "volume": data["Volume"].iloc[-1],
        "postprocess": ["trailing_stop"],
    }

    # Sending a POST request with JSON data
    response = requests.post(hook_url, json=data)

    if response.status_code == 200:
        try:
            logging.info(f"Order sent successfully for {symbol}")
        except requests.exceptions.JSONDecodeError:
            logging.error("Response is not in JSON format.")
    else:
        logging.error(f"HTTP Error encountered: {response}")
        

async def calc_strat(ticker, data):
    """
    Calculates multiple strategies using the ta library
    @TODO: If websocket goes offline then it's missing those candles in between when the system was offline.
    """
    global last_buy_timestamp
    df = pd.DataFrame(data)

    logging.info(f"Calculating strategy for {ticker}")

    try:
        # Check if 'Epoch' is already the index
        if df.index.name != "Epoch":
            # Convert 'Epoch' column to datetime and set as index
            df["Epoch"] = pd.to_datetime(df["Epoch"], errors="coerce")
            df.set_index("Epoch", inplace=True)
        else:
            # Convert the index to datetime
            df.index = pd.to_datetime(df.index, errors="coerce")

        # Check for any null values in 'Epoch' index
        if df.index.isnull().any():
            logging.error("Error converting 'Epoch' to datetime. Some values are NaT.")
            return
        else:
            logging.info("Index set successfully.")
    except Exception as e:
        logging.error(f"Failed to set index: {e}")

    try:
        # Calculate MACD
        try:
            macd = ta.macd(df["Close"])
            df = df.join(macd)
            logging.info("MACD calculated successfully.")
        except Exception as e:
            logging.error(f"Error calculating MACD: {e}")
            raise

        # Calculate RSI
        try:
            df["RSI_14"] = ta.rsi(df["Close"])
            logging.info("RSI calculated successfully.")
        except Exception as e:
            logging.error(f"Error calculating RSI: {e}")
            raise

        # Calculate Bollinger Bands
        try:
            bb = ta.bbands(df["Close"])
            df = df.join(bb)
            logging.info("Bollinger Bands calculated successfully.")
        except Exception as e:
            logging.error(f"Error calculating Bollinger Bands: {e}")
            raise

        logging.info("Technical indicator macd, rsi, bb, calculated successfully.")

    except Exception as e:
        logging.error(f"Error calculating technical indicators: {e}")

    try:
        anomalies = pd.DataFrame(index=df.index)

        # MACD anomalies
        anomalies["MACD_Buy"] = (df["MACD_12_26_9"] > df["MACDs_12_26_9"]) & (
            df["MACD_12_26_9"].shift(1) < df["MACDs_12_26_9"].shift(1)
        )
        anomalies["MACD_Sell"] = (df["MACD_12_26_9"] < df["MACDs_12_26_9"]) & (
            df["MACD_12_26_9"].shift(1) > df["MACDs_12_26_9"].shift(1)
        )

        # RSI anomalies
        anomalies["RSI_Buy"] = (df["RSI_14"] > 30) & (df["RSI_14"].shift(1) < 30)
        anomalies["RSI_Sell"] = (df["RSI_14"] < 70) & (df["RSI_14"].shift(1) > 70)

        # Bollinger Bands anomalies
        anomalies["BB_Buy"] = df["Close"] < df["BBL_5_2.0"]
        anomalies["BB_Sell"] = df["Close"] > df["BBU_5_2.0"]

    except Exception as e:
        logging.error(f"Error detecting anomalies: {e}")
        return pd.DataFrame()

    # Check the last xxx bars for buy/sell signals
    recent_anomalies = anomalies.tail(25)

    buy_condition = (
        recent_anomalies["MACD_Buy"].any() and recent_anomalies["RSI_Buy"].any()
    )
    sell_condition = (
        recent_anomalies["MACD_Sell"].any() and recent_anomalies["RSI_Sell"].any()
    )
 
    current_timestamp = df.index[-1].timestamp()

    if buy_condition:
        if ticker not in last_buy_timestamp or (
            current_timestamp - last_buy_timestamp[ticker]
        ) > (cooldown_period * 60):
            logging.info(f"Buy condition met in {ticker}")   
            send_order("buy", ticker, data)
            last_buy_timestamp[ticker] = current_timestamp

    # @TODO: For sell condition maybe we should check last time and ALSO if sell conditions are later than the buy.
    if sell_condition:
        logging.info(f"Sell condition met in {ticker}")
        send_order("sell", ticker, data)


async def read_data_from_marketstore(symbol):
    # Define the query parameters
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


async def get_list(key):
    list_data = await redis.lrange(key, 0, -1)
    if list_data:
        list_data = json.loads(list_data[0].decode("utf-8"))
    return list_data


async def spawn_calc():
    # Fetch the redis list
    earnings = await get_list(list_name)

    # Loop through the list and calculate the strategy
    if earnings:
        for symbol in earnings:
            data = await read_data_from_marketstore(symbol)
            await calc_strat(symbol, data)


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
    scheduler.add_job(fetch_earnings_calendar, "interval", minutes=1)
    scheduler.add_job(spawn_calc, "interval", minutes=1, seconds=0)

    await asyncio.gather(scheduler_task(scheduler))


if __name__ == "__main__":
    asyncio.run(main())
