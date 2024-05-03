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
env = os.getenv("COPILOT_ENVIRONMENT_NAME", "dev")
app = os.getenv("COPILOT_APPLICATION_NAME", "dev")
tv_sig = os.getenv("TRADINGVIEW_SECRET")
hook_url = os.getenv("EARNYEARN_ORDER_ENDPOINT")


auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})
stream = "wss://stream.data.alpaca.markets/v2/sip"

# Set the display options
pd.set_option("display.max_columns", None)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("max_colwidth", None)
pd.set_option("display.max_rows", None)
bar_number = 42
subs = []
websocket_connected = False
dataframes = {}

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


def send_order(action, symbol, data):
    """
    Sends a POST request to the TradingView webhook URL
    required fields: action, comment, low, high, close, volume, interval, signature, ticker, trailing
    """
    data = {
        "action": action,
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
        print(f"HTTP Error encountered: {response.status_code}")


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

    # make the subs list unique just in case there are duplicates
    subs = list(set(subs))

    await socket(subs)


async def process_bar_data(data, strat):
    """
    Processes the bar data received from the WebSocket
    Updates the dataframes dictionary with the latest data
    Calls the calc_strat function to calculate the strategy
    Saves the data to a JSON file for future reference in data folder
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

    for symbol, group in df.groupby("symbol"):
        group = group.set_index(
            "timestamp"
        )  # Use timestamp as index for MACD calculation

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
                continue

        await calc_strat(strat, symbol)


async def calc_strat(strat, symbol):
    """
    Calculates multiple strategies using the ta library
    """
    if isinstance(dataframes[symbol], pd.DataFrame) and len(dataframes[symbol]) < 35:
        print(f"Not enough data to calculate 📈 {strat} 📈 on {symbol}")
        return

    if strat == "macd":
        print(f"🤓 Calculating 📈 {strat} 📈 for {symbol}")
        # print(finnhub_client.price_target(symbol))
        # @ TODO: index reset to accomodate the json files indexing this may not be reliable for order of data
        dataframes[symbol] = dataframes[symbol].reset_index(drop=True)
        # @ TODO: need a tweakable time interval to calculate the MACD
        # dataframes[symbol] = dataframes[symbol]["close"].resample("15T").mean()

        macd = dataframes[symbol].ta.macd(
            close="close", fast=12, slow=26, signal=9
        )  # Apply MACD with default parameters (fast=12, slow=26, signal=9)

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
        await asyncio.sleep(1)


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())
