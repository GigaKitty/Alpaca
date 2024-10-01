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


def parse_datetime(dt_str):
    try:
        return datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    except ValueError as e:
        logging.error(f"Error parsing datetime: {e}")
        return None


async def calc_strat(ticker, data):
    """
    Calculate volatility of the market data and determine the trading strategy.
    """
    if data is None:
        logging.error(f"No data found for {ticker}")
        return
        # Calculate 1-minute returns and volatility
        data["Returns"] = data["Close"].pct_change()
        data["Volatility"] = (
            data["Returns"].rolling(window=5).std()
        )  # Short 5-minute rolling window
        data["ATR"] = ta.atr(
            data["High"], data["Low"], data["Close"], length=5
        )  # ATR for 1-minute data

        # Strategy: Detect high volatility periods
        volatility_threshold = data["Volatility"].mean() + data["Volatility"].std()
        data["High_Volatility_Signal"] = data["Volatility"] > volatility_threshold

        # Output results with high volatility signals
        print(data[data["High_Volatility_Signal"]])

    # Calculate the volatility
    data.ta.atr(length=14)

    # Determine the trading strategy
    if data["Close"].iloc[-1] > data["Close"].iloc[-2]:
        signal = "buy"
    elif data["Close"].iloc[-1] < data["Close"].iloc[-2]:
        signal = "sell"
    else:
        signal = "hold"

    print(f"Trading signal for {ticker}: {signal}")

    return signal


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
        "low": data["Low"].iloc[-1],
        "open": data["Open"].iloc[-1],
        # "side": "long",
        "risk": os.getenv("EARNYEARN_RISK", 0.0001),
        "signature": tv_sig,
        "ticker": symbol,
        "trailing": 1,
        "volume": data["Volume"].iloc[-1],
    }

    # Sending a POST request with JSON data
    response = requests.post(hook_url, json=data)

    if response.status_code == 200:
        try:
            print("Pass", response.json())
            print(data)
        except requests.exceptions.JSONDecodeError:
            print("Response is not in JSON format.", response)
    else:
        print(f"HTTP Error encountered: {response}")


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
            await redis.lpush(f"logs:{ticker}", json.dumps(item))
            await store_in_marketstore(item)
            market_data = await read_data_from_marketstore(item)
            await calc_strat(ticker, market_data)

        else:
            print(f"Skipping message: {item}")


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
        #print(f"Published message: {message} to list: {list_name}")
    except aioredis.exceptions.TimeoutError:
        print(f"Timeout error while publishing message: {message} to list: {list_name}")
    except aioredis.exceptions.RedisError as e:
        print(
            f"Redis error: {e} while publishing message: {message} to list: {list_name}"
        )


async def get_all_positions():
    positions = api.get_all_positions()
    return [position.symbol for position in positions]


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
        print(f"Published message: {filtered_stocks} to list: volatilityvulture_list")
        # monitor the volatility of the stocks using supertrend strategy
        for stock in filtered_stocks:
            print(f"Processing stock: {stock}")


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



# import pandas as pd
# import pandas_ta as ta

# # Sample data for one minute interval (Replace with your actual DataFrame)
# # Your DataFrame should have columns: ['open', 'high', 'low', 'close', 'volume']
# df = pd.DataFrame({
#     'open': [/* your data */],
#     'high': [/* your data */],
#     'low': [/* your data */],
#     'close': [/* your data */],
#     'volume': [/* your data */],
# })

# # Inputs
# atr_period = 10  # ATR Period (default 10)
# atr_multiplier = 3.0  # ATR Multiplier (default 3.0)

# # Calculate ATR
# df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=atr_period)

# # SuperTrend calculation
# df['hl2'] = (df['high'] + df['low']) / 2  # HL2 (same as Pine Script 'hl2')

# # Calculate upper and lower bands
# df['upperband'] = df['hl2'] - (atr_multiplier * df['atr'])
# df['lowerband'] = df['hl2'] + (atr_multiplier * df['atr'])

# # Initialize columns for trend, up and down band
# df['trend'] = 0
# df['prev_upperband'] = df['upperband'].shift(1)
# df['prev_lowerband'] = df['lowerband'].shift(1)
# df['prev_close'] = df['close'].shift(1)

# # Logic for upper and lower bands adjustment
# df['upperband'] = df.apply(lambda row: max(row['upperband'], row['prev_upperband']) if row['prev_close'] > row['prev_upperband'] else row['upperband'], axis=1)
# df['lowerband'] = df.apply(lambda row: min(row['lowerband'], row['prev_lowerband']) if row['prev_close'] < row['prev_lowerband'] else row['lowerband'], axis=1)

# # Logic for trend change
# df['trend'] = df.apply(lambda row: 1 if (row['prev_trend'] == -1 and row['close'] > row['prev_lowerband']) else
#                                 -1 if (row['prev_trend'] == 1 and row['close'] < row['prev_upperband']) else row['prev_trend'], axis=1)

# # Generate buy and sell signals
# df['buy_signal'] = (df['trend'] == 1) & (df['trend'].shift(1) == -1)
# df['sell_signal'] = (df['trend'] == -1) & (df['trend'].shift(1) == 1)

# # Display relevant columns (close price, SuperTrend, buy/sell signals)
# result = df[['close', 'upperband', 'lowerband', 'trend', 'buy_signal', 'sell_signal']]

# import ace_tools as tools; tools.display_dataframe_to_user(name="SuperTrend Data", dataframe=result)

# # Add your logic here to act on buy/sell signals
