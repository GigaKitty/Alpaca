import datetime
import finnhub
import os
import json
import time
import websockets
import asyncio
import pandas as pd
import pandas_ta as ta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# from apscheduler.schedulers.blocking import BlockingScheduler


api_key = os.getenv("APCA_API_KEY_ID")
api_sec = os.getenv("APCA_API_SECRET_KEY")
auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})
stream = "wss://stream.data.alpaca.markets/v2/sip"
subs = []
websocket_connected = False
dataframes = {}


async def start_scheduler():
    scheduler = AsyncIOScheduler()
    # scheduler.add_job(fetch_earnings_calendar, "interval", minutes=1)
    # Check every hour for earnings data from 09:30EST (14:30UTC) to 16:00EST (21:00UTC) on weekdays (Mon-Fri)
    scheduler.add_job(
        fetch_earnings_calendar,
        "cron",
        day_of_week="mon-fri",
        timezone="America/New_York",
        hour="8-19",
        minute="*/1",
    )
    scheduler.start()


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
            # print(earning["symbol"])
            subs.append(earning["symbol"])

    else:
        print("No earnings data found for the specified date range.")
    # print(subs)
    await socket(subs)

# Sends a json webhook request to alpaca to place an order
# async def order():


async def process_bar_data(data):
    global dataframes
    data = json.loads(data)
    # Initialize a DataFrame to store parsed data
    df = pd.DataFrame(data)

    if "S" not in df.columns:
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

    # Remove open, high, low, volume from dataframe this may or may not save us some memory
    # df = df.drop(columns=["open", "high", "low", "volume", "n", "vw"])

    if df["close"].isnull().values.any():
        print("DataFrame contains NaN values.")
        return

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

        # Optionally, limit the size of the DataFrame to keep only recent data
        dataframes[symbol] = dataframes[symbol].tail(3600)
        # Check for MACD crossover
        # Apply MACD with default parameters (fast=12, slow=26, signal=9)
        # Check if we have enough data to calculate MACD
        if len(dataframes[symbol]) < 35:
            # print(f"Not enough data for {symbol} to calculate MACD")
            # print(dataframes[symbol])
            continue

        macd = dataframes[symbol].ta.macd(close="close", fast=12, slow=26, signal=9)
        if (
            macd["MACD_12_26_9"].iloc[-1] > macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] < macd["MACDh_12_26_9"].iloc[-2]
        ):
            # this is where we sendthe we
            print(
                f"MACD bullish crossover for {symbol} at {group['timestamp'].iloc[-1]}"
            )
        elif (
            macd["MACD_12_26_9"].iloc[-1] < macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] > macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(
                f"MACD bearish crossover for {symbol} at {group['timestamp'].iloc[-1]}"
            )

        # print(dataframes[symbol])
        # print(macd)


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
                    await process_bar_data(data)
                except websockets.ConnectionClosed:
                    print("WebSocket connection closed")
                    websocket_connected = False
                    break
        else:
            print("Authentication failed.")
            websocket_connected = False


async def main():
    await fetch_earnings_calendar()
    # await socket(subs)
    while True:
        await asyncio.sleep(1)  # Sleep for 1 seconds

if __name__ == "__main__":
    asyncio.run(main())
