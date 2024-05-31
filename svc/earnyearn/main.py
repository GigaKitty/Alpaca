import asyncio
import finnhub
import json
import logging
import os
import pandas as pd
import numpy as np
import pandas_ta as ta
import pymarketstore as pymkts
import redis.asyncio as aioredis
import requests
import datetime
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler


########################################
### SETUP ENV
########################################
api_key = os.getenv("APCA_API_KEY_ID")
api_sec = os.getenv("APCA_API_SECRET_KEY")
app = os.getenv("COPILOT_APPLICATION_NAME", "dev")
bar_number = 42
dataframes = {}
env = os.getenv("COPILOT_ENVIRONMENT_NAME", "dev")
fetch_pause = 60
hook_url = os.getenv("EARNYEARN_ORDER_ENDPOINT")
stream = "wss://stream.data.alpaca.markets/v2/sip"
earnings = []
timeframe = "1Min"
attribute_group = "OHLCV"
tv_sig = os.getenv("TRADINGVIEW_SECRET")

# Auth Message json
auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

# Set the display options to NO LIMITS!!!
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)

# Redis connection details
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

marketstore_host = os.getenv("MARKETSTORE_HOST", "localhost")
marketstore_client = pymkts.Client(f"{marketstore_host}/rpc")
logging.basicConfig(level=logging.INFO)
########################################
########################################


async def fetch_earnings_calendar():
    """
    Fetches the earnings calendar for the next 7 days from Finnhub API
    List of symbols is stored in the earnings global variable
    Updates the earnings list with the latest earnings data
    @SEE: https://finnhub.io/docs/api/earnings-calendar
    """
    global earnings

    # Configure your Finnhub API key here
    finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

    # reset earnings to empty list
    earnings = []

    # Define the date range for the earnings calendar
    # For example, the next 7 days from today
    start_date = datetime.datetime.now().date()
    end_date = (
        datetime.datetime.now() + datetime.timedelta(days=os.getenv("FINNHUB_DAYS", 7))
    ).date()

    # Fetch the earnings calendar
    earnings_calendar = finnhub_client.earnings_calendar(
        _from=start_date.strftime("%Y-%m-%d"),
        to=end_date.strftime("%Y-%m-%d"),
        symbol="",
        international=False,
    )

    # Check if there are earnings in the fetched data
    if "earningsCalendar" in earnings_calendar:
        for earning in earnings_calendar["earningsCalendar"]:
            if (
                earning["year"] == datetime.datetime.now().year  # This year
                and earning["epsEstimate"] is not None
                and earning["epsEstimate"] >= 1
                and earning["revenueEstimate"] is not None
                and earning["revenueEstimate"] >= 2.5e8
            ):  # Filter out low volume stocks 2.5e8 is basically 250million
                earnings.append(earning["symbol"])

    else:
        print("😭 No earnings data found for the specified date range.")

    print(f"📊 {len(earnings)} symbols added to the earnings list. 📊")
    print(f"{earnings}")


def send_order(action, symbol, data):
    """
    Sends a POST request to the TradingView webhook URL
    required fields: action, comment, low, high, close, volume, interval, signature, ticker, trailing
    """
    data = {
        "action": action,
        "side": "buy",
        "comment": "macd-earnyearn",
        "low": data["low"].iloc[-1],
        "high": data["high"].iloc[-1],
        "close": data["close"].iloc[-1],
        "volume": data["volume"].iloc[-1],
        "interval": "1m",
        "signature": tv_sig,
        "ticker": symbol,
        "trailing": True,
    }

    # Sending a POST request with JSON data
    response = requests.post(hook_url, json=data)

    if response.status_code == 200:
        try:
            print("Pass", response.json())
        except requests.exceptions.JSONDecodeError:
            print("Response is not in JSON format.", response)
    else:
        print(f"HTTP Error encountered: {response}")


async def calc_strat(ticker, data, strat):
    """
    Calculates multiple strategies using the ta library
    """
    df = pd.DataFrame(data)

    try:
        df["Epoch"] = pd.to_datetime(df["Epoch"], errors="coerce")
        if df["Epoch"].isnull().any():
            logging.error("Error converting 'Epoch' to datetime. Some values are NaT.")
        else:
            df.set_index("Epoch", inplace=True)
            logging.info("Index set successfully.")
    except Exception as e:
        logging.error(f"Failed to set index: {e}")

    try:
        # Calculate MACD
        macd = ta.macd(df["Close"])
        df = df.join(macd)

        # Calculate RSI
        df["RSI"] = ta.rsi(df["Close"])

        # Calculate Bollinger Bands
        bb = ta.bbands(df["Close"])
        df = df.join(bb)

        logging.info("Technical indicators calculated successfully.")
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

        # Combine buy and sell signals
        anomalies["Buy"] = (
            anomalies["MACD_Buy"] | anomalies["RSI_Buy"] | anomalies["BB_Buy"]
        )
        anomalies["Sell"] = (
            anomalies["MACD_Sell"] | anomalies["RSI_Sell"] | anomalies["BB_Sell"]
        )

    except Exception as e:
        logging.error(f"Error detecting anomalies: {e}")
        return pd.DataFrame()

    anomalies = detect_anomalies(df)

    print("Buy/Sell signals detected:")
    print(anomalies[anomalies["Buy"] | anomalies["Sell"]])

    return
    if len(data) < bar_number * timeframe:
        return print(
            f"🤖 Not enough data to calculate 📈 {strat} 📈 on {ticker} there are {len(data)} rows needs {bar_number}"
        )

    return

    if strat == "macd":
        print(f"🤓 Calculating 📈 {strat} 📈 for {ticker}")

        # dataframes[symbol] = (
        #    dataframes[symbol]["close"].resample(f"{timeframe}min").mean()
        # )

        macd = data.ta.macd(
            close="close", fast=12, slow=26, signal=9
        )  # Apply MACD with default parameters (fast=12, slow=26, signal=9)

        if (
            macd["MACD_12_26_9"].iloc[-1] > macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] < macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD Bullish🔺🐂🔺 crossover for {ticker}")
            send_order("buy", ticker, data)
        elif (
            macd["MACD_12_26_9"].iloc[-1] < macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] > macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD Bearish🔻🐻🔻 crossover for {ticker}")
            send_order("sell", ticker, data)
    # @TODO: Add more strategies here


def parse_datetime(dt_str):
    try:
        return datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    except ValueError as e:
        logging.error(f"Error parsing datetime: {e}")
        return None


async def store_in_marketstore(data):
    """
    Store the data in Marketstore.
    """
    try:
        required_fields = ["S", "t", "o", "h", "l", "c", "v"]
        if not all(field in data for field in required_fields):
            raise ValueError(f"Missing one of the required fields: {required_fields}")

        epoch_time = parse_datetime(data["t"])

        df = np.array(
            [
                (
                    epoch_time,
                    data.get("o", 0.0),
                    data.get("h", 0.0),
                    data.get("l", 0.0),
                    data.get("c", 0.0),
                    data.get("v", 0.0),
                )
            ],
            dtype=[
                ("Epoch", "i8"),  # int64
                ("Open", "f8"),  # float64
                ("High", "f8"),  # float64
                ("Low", "f8"),  # float64
                ("Close", "f8"),  # float64
                ("Volume", "f8"),  # float64
            ],
        )

        # Determine the symbol and timeframe
        symbol = data["S"]

        print(f"Storing marketstore data for symbol {symbol} with data: {df}")

        # Write to Marketstore
        marketstore_client.write(df, f"{symbol}/{timeframe}/{attribute_group}")
        print(f"Successfully stored data for {symbol}")
    except Exception as e:
        print(f"Error storing data: {e}")


async def read_data_from_marketstore(data):
    symbol = data["S"]

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


async def process_message(redis, message):
    """
    Process the message if it meets the filtering criteria and log to Redis.
    """
    data = json.loads(message)

    # Filter based on the ticker symbol
    filtered_data = [
        item for item in data if item.get("S") in earnings and item.get("T") == "b"
    ]

    for item in filtered_data:
        ticker = item.get("S")
        if ticker:
            print(f"Processing message for {ticker}: {item}")
            # Log message to Redis list
            await redis.lpush(f"logs:{ticker}", json.dumps(item))
            await store_in_marketstore(item)
            market_data = await read_data_from_marketstore(item)
            await calc_strat(ticker, market_data, "macd")

        else:
            print(f"Skipping message: {item}")


async def redis_listener():
    redis = aioredis.from_url(
        f"redis://{redis_host}:{redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe("stocks_channel")

    async for message in pubsub.listen():
        if message["type"] == "message":
            await process_message(redis, message["data"])


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

    await asyncio.gather(redis_listener(), scheduler_task(scheduler))


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())
