import datetime
import finnhub
import os
import json
import requests
import websockets
import asyncio
import pandas as pd
import pandas_ta as ta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

########################################
### SETUP ENV
########################################
api_key = os.getenv("APCA_API_KEY_ID")
api_sec = os.getenv("APCA_API_SECRET_KEY")
app = os.getenv("COPILOT_APPLICATION_NAME", "dev")
bar_number = 42
dataframes = {}
env = os.getenv("COPILOT_ENVIRONMENT_NAME", "dev")
hook_url = os.getenv("EARNYEARN_ORDER_ENDPOINT")
stream = "wss://stream.data.alpaca.markets/v2/sip"
subs = []
timeframe = 1
tv_sig = os.getenv("TRADINGVIEW_SECRET")
websocket_connected = False

# Auth Message json
auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

# Set the display options to NO LIMITS!!!
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)
########################################
########################################


async def start_scheduler():
    """
    Runs on a specific schedule and shuts down after hours
    """
    scheduler = AsyncIOScheduler()
    final_hour = 16
    print("Starting the scheduler 📅 ...")
    # Schedule fetch_earnings_calendar to run every minute from 09:30EST to 16:00EST on weekdays
    job = scheduler.add_job(
        fetch_earnings_calendar,
        CronTrigger(
            day_of_week="mon-fri",
            hour=f"9-{final_hour}",
            minute="*/1",
            timezone="America/New_York",
        ),
    )

    scheduler.add_job(
        lambda: scheduler.remove_job(job.id),
        CronTrigger(
            day_of_week="mon-fri",
            hour=final_hour,
            minute=0,
            timezone="America/New_York",
        ),
    )

    for job in scheduler.get_jobs():
        print(f"Job: {job}")

    scheduler.start()


async def fetch_earnings_calendar():
    """
    Fetches the earnings calendar for the next 7 days from Finnhub API
    Provides a list of symbols for the WebSocket subscription
    List of symbols is stored in the subs global variable
    Symbols are used to subscribe to the WebSocket for real-time data
    Updates the subs list with the latest earnings data
    """
    global subs

    # Configure your Finnhub API key here
    finnhub_client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

    # reset subs to empty list
    subs = []

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
        print("😭😭😭No earnings data found for the specified date range.")

    print(f"📊 {len(subs)} symbols added to the WebSocket subscription list. 📊")

    await socket(subs)


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


def convert_timestamp(ts):
    """
    For some reason the timestamp data is inconsistent sometimes showing as a datetime format and sometimes as an epoch
    This function converts the timestamp
    """
    if isinstance(ts, int):
        # Convert from epoch to datetime
        return pd.to_datetime(ts, unit="ms").tz_localize("UTC")
    else:
        # Convert string to datetime
        dt = pd.to_datetime(ts)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # The timestamp is timezone-naive, localize it
            return dt.tz_localize("UTC")
        else:
            # The timestamp is timezone-aware, convert it
            return dt.tz_convert("UTC")


async def process_bar_data(data, strat):
    """
    Processes the bar data received from the WebSocket
    Updates the dataframes dictionary with the latest data
    Calls the calc_strat function to calculate the strategy
    Saves the data to a JSON file for future reference in data folder
    @SEE: https://docs.alpaca.markets/docs/real-time-stock-pricing-data#bars
    """
    global dataframes

    if isinstance(data, str):
        data = json.loads(data)
    else:
        print(f"Unexpected response type: {type(data)}")
        return
    df = pd.DataFrame(data)

    if "S" not in df.columns:
        return

    if df.isnull().values.any():
        print("DataFrame contains NaN values.")
        return

    # Ensure the 'o', 'h', 'l', 'c', and 'v' columns are numeric
    df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].apply(pd.to_numeric)

    # convert t o h l c v df columns to float
    df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)

    # conform with the data structure for the MACD calculation
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

    df["timestamp"] = df["timestamp"].apply(convert_timestamp)

    for symbol, group in df.groupby("symbol"):
        # Check if the symbol already has a DataFrame
        if symbol in dataframes:
            # Append the new data
            dataframes[symbol] = pd.concat([dataframes[symbol], group])

            dataframes[symbol].to_json(
                f"./data/{symbol}.json", orient="records", lines=True
            )
        else:
            # Create a new DataFrame for this symbol
            if os.path.exists(f"./data/{symbol}.json"):
                load_df = pd.read_json(
                    f"./data/{symbol}.json", orient="records", lines=True
                )

                dataframes[symbol] = pd.concat([load_df, group])
            else:
                # If the file doesn't exist, just assign group to dataframes[symbol]
                dataframes[symbol] = group
                print(f"New dataframe group {symbol}")

        # This is attempting to convert all timestamps to a uniform format and will apply on all rows in the timestamp column for the dataframe
        dataframes[symbol]["timestamp"] = dataframes[symbol]["timestamp"].apply(
            convert_timestamp
        )

        await calc_strat(strat, symbol)


async def calc_strat(strat, symbol):
    """
    Calculates multiple strategies using the ta library
    """
    if (
        isinstance(dataframes[symbol], pd.DataFrame)
        and len(dataframes[symbol]) < bar_number * timeframe
    ):
        return print(
            f"🤖 Not enough data to calculate 📈 {strat} 📈 on {symbol} there are {len(dataframes[symbol])} rows needs {bar_number}"
        )

    if strat == "macd":
        print(f"🤓 Calculating 📈 {strat} 📈 for {symbol}")
        # @ TODO: index reset to accomodate the json files indexing this may not be reliable for order of data
        # dataframes[symbol] = dataframes[symbol].reset_index(drop=True)
        # @ TODO: need a tweakable time interval to calculate the MACD
        # dataframes[symbol] = dataframes[symbol]["close"].resample("15T").mean()

        # macd = macd.reshet_index(drop=True)
        dataframes[symbol] = dataframes[symbol].reset_index(drop=True)
        macd = dataframes[symbol].ta.macd(
            close="close", fast=12, slow=26, signal=9
        )  # Apply MACD with default parameters (fast=12, slow=26, signal=9)
        # print(macd)
        # print(macd)
        # return
        if (
            macd["MACD_12_26_9"].iloc[-1] > macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] < macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD Bullish🔺🐂🔺 crossover for {symbol}")
            send_order("buy", symbol, dataframes[symbol])
        elif (
            macd["MACD_12_26_9"].iloc[-1] < macd["MACDh_12_26_9"].iloc[-1]
            and macd["MACD_12_26_9"].iloc[-2] > macd["MACDh_12_26_9"].iloc[-2]
        ):
            print(f"MACD Bearish🔻🐻🔻 crossover for {symbol}")
            send_order("sell", symbol, dataframes[symbol])
    # @TODO: Add more strategies here


# Subscribe: {"action": "subscribe", "trades": ["AAPL"], "quotes": ["AMD", "CLDR"], "bars": ["*"]}
# Unsubscribe: {"action":"unsubscribe","trades":["VOO"],"quotes":["IBM"]}
# @SEE: https://docs.alpaca.markets/docs/real-time-stock-pricing-data
async def socket(subs):
    """
    Connects to the WebSocket and subscribes to the provided symbols
    Attempts to reconnect if the connection is closed
    Subscribes to the bars data for the provided symbols
    """
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
            # print the number of unsubscribed symbols
            print(f"👎 Unsubscribing from {len(subs)} symbols. 👎")
            await websocket.send(unsub_message)
            # print the number of subscribed symbols
            print(f"👍 Subscribing to {len(subs)} symbols. 👍")
            await websocket.send(sub_message)

            while True:
                try:
                    data = await websocket.recv()
                    await process_bar_data(data, "macd")
                except websockets.ConnectionClosed:
                    print(f"😭 WebSocket connection closed. Reconnecting...🔌")
                    websocket_connected = False
                    break
        else:
            print("Authentication failed.")
            websocket_connected = False


async def main():
    """
    Main function to start the scheduler and run the event loop
    """
    await start_scheduler()
    while True:
        # await fetch_earnings_calendar()
        await asyncio.sleep(1)


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())
