import datetime
import finnhub
import os
import json
import time
import requests
import websockets
import asyncio
import sys
import pandas as pd
import pandas_ta as ta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

########################################
### SETUP ENV
########################################
api_key = os.getenv("APCA_API_KEY_ID")
api_sec = os.getenv("APCA_API_SECRET_KEY")
env = os.getenv("COPILOT_ENVIRONMENT_NAME", "dev")
tv_sig = os.getenv("TRADINGVIEW_SECRET")

auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})
stream = "wss://stream.data.alpaca.markets/v2/sip"

# @TODO: Make this URL dynamic but how based on other services?
hook_url = "https://signalspit.dev.alpaca.gigakitty.com/market"
# Set the display options
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)
bar_number = 42
subs = []
websocket_connected = False
dataframes = {}
client = StockHistoricalDataClient(api_key=api_key, secret_key=api_sec)


########################################
########################################


async def get_bars(symbol):

    # Convert to dataframe
    bars.df
    return bars.df
    ###########


async def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Check every hour for earnings data from 09:30EST (14:30UTC) to 16:00EST (21:00UTC) on weekdays (Mon-Fri)
    scheduler.add_job(
        fetch_earnings_calendar,
        "cron",
        day_of_week="mon-fri",
        timezone="America/New_York",
        minute="*/1",
    )
    scheduler.start()


def send_order(action, symbol, data):
    print(data)
    data = {
        "action": action,
        "comment": "macd-earnyearn",
        "low": data[symbol]["low"].iloc[-1],
        "high": data[symbol]["high"].iloc[-1],
        "close": data[symbol]["close"].iloc[-1],
        "volume": data[symbol]["volume"].iloc[-1],
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
        print(f"HTTP Error encountered: {response.status_code}")


async def fetch_earnings_calendar():
    global subs

    # Configure your Finnhub API key here
    finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

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
            subs.append(earning["symbol"])

    else:
        print("No earnings data found for the specified date range.")

    await socket(subs)


async def process_bar_data(data, strat):
    global dataframes

    data = json.loads(data)
    df = pd.DataFrame(data)

    if "S" not in df.columns:
        return

    if df.isnull().values.any():
        print("DataFrame contains NaN values.")
        return

    #  Ensure the 'o', 'h', 'l', 'c', and 'v' columns are numeric
    df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].apply(pd.to_numeric)

    # convert t o h l c v df columns to float
    df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)

    # this is to conform with the data structure for the MACD calculation
    df = df.rename(
        columns={
            "S": "symbol",
            "t": "timestamp",
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )

    for symbol, group in df.groupby("symbol"):
        group = group.set_index(
            "timestamp"
        )  # Use timestamp as index for MACD calculation

        # Check if the symbol already has a DataFrame
        if symbol in dataframes:
            # Append the new data
            dataframes[symbol] = pd.concat([dataframes[symbol], group])
        else:
            # Create a new DataFrame for this symbol
            dataframes[symbol] = group
            #####
            # request_params = StockBarsRequest(
            #    symbol_or_symbols=symbol, timeframe=TimeFrame.Minute, limit=bar_number
            # )
            # print(f"fetching bar data for {symbol} to build dataframe")
            # bars = client.get_stock_bars(request_params)
            # dataframes[symbol] = pd.concat([bars.df, group])
            print(f"New dataframe group {symbol}")

        dataframes[symbol] = dataframes[symbol].tail(
            3600
        )  # Apply MACD with default parameters (fast=12, slow=26, signal=9)
        if (
            len(dataframes[symbol]) < 35
        ):  # Check if we have enough data to calculate MACD
            print(f"Not enough data to calculate {strat} on {symbol}")
            continue

        await calc_strat(strat, symbol)


async def calc_strat(strat, symbol):
    print(f"Calculating {strat} for {symbol}")
    print(dataframes[symbol])
    if strat == "macd":
        macd = dataframes[symbol].ta.macd(close="close", fast=12, slow=26, signal=9)
        if (
            macd["MACD_12_26_9"].iloc[-1] > macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] < macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD bullish crossover for {symbol}")
            send_order("buy", symbol, dataframes[symbol])
        elif (
            macd["MACD_12_26_9"].iloc[-1] < macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] > macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD bearish crossover for {symbol}")
            send_order("sell", symbol, dataframes[symbol])
    # @TODO: Add more strategies here


# Subscribe: {"action": "subscribe", "trades": ["AAPL"], "quotes": ["AMD", "CLDR"], "bars": ["*"]}
# Unsubscribe: {"action":"unsubscribe","trades":["VOO"],"quotes":["IBM"]}
# @SEE: https://docs.alpaca.markets/docs/real-time-stock-pricing-data
async def socket(subs):
    global websocket_connected, auth_message

    async with websockets.connect(stream) as websocket:

        if not websocket_connected:
            await websocket.send(auth_message)

            response = await websocket.recv()
            print(f"Authentication response: {response}")
        else:
            print("Already connected to the WebSocket.")
            response = [{"T": "success", "msg": "authenticated"}]

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
            unsub_message = json.dumps(
                {
                    "action": "unsubscribe",
                    "bars": ["*"],
                }
            )
            sub_message = json.dumps(
                {
                    "action": "subscribe",
                    "bars": subs,
                }
            )

            print("Authentication successful. Connected to the WebSocket.")
            websocket_connected = True
            # To make things easy we'll just unsub and re-sub with fresh ones.
            await websocket.send(unsub_message)
            await websocket.send(sub_message)

            while True:
                try:
                    data = await websocket.recv()
                    await process_bar_data(data, "macd")
                except websockets.ConnectionClosed:
                    print(f"WebSocket connection closed we retrying...")
                    websocket_connected = False
        else:
            print("Authentication failed.")
            websocket_connected = False


async def main():
    await fetch_earnings_calendar()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
