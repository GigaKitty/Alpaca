import datetime
import finnhub
import os
import json
import time
import websockets
import asyncio
from celery import Celery
from celery.schedules import crontab


# Configure Celery to use AWS SQS as the message broker
app = Celery(
    "worker",
    broker="sqs://AWS_ACCESS_KEY_ID:AWS_SECRET_ACCESS_KEY@",
    backend=None,
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

app.conf.beat_schedule = {
    "add-every-5-minutes": {
        "task": "tasks.fetch_earnings_calendar",
        "schedule": crontab(minute="*/5", hour="14-23", day_of_week="mon-fri"),
    },
}

# Function to check if the value is not None and is a number
def is_valid(value):
    if value is None:
        return 0

    if value == 0:
        return 0

    return value


def good_buy(earning):
    eps_growth_threshold = 0.1  # 5%
    revenue_growth_threshold = 0.1  # 3%

    actual = is_valid(earning["epsActual"])
    estimate = is_valid(earning["epsEstimate"])
    rev_act = is_valid(earning["revenueActual"])
    rev_est = is_valid(earning["revenueEstimate"])

    if actual == False or estimate == False or rev_act == False or rev_est == False:
        return False

    # print(earning)
    # print(actual, estimate, rev_act, rev_est)
    eps_growth = (actual - estimate) / estimate

    revenue_growth = rev_act - rev_est / rev_est

    # Determine if it's a good buy
    is_good_buy = (
        eps_growth > eps_growth_threshold and revenue_growth > revenue_growth_threshold
    )

    # Results by percentage
    eps_growth_percentage = eps_growth * 100
    revenue_growth_percentage = revenue_growth * 100

    return is_good_buy


# Check every hour for earnings data from 09:30EST (14:30UTC) to 16:00EST (21:00UTC) on weekdays (Mon-Fri)
@app.task
def fetch_earnings_calendar():
    buys = []
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
            if good_buy(earning) == True:
                buys.append(earning["symbol"])
    else:
        print("No earnings data found for the specified date range.")
    print(buys)
    # await socket(buys)


# Subscribe: {"action": "subscribe", "trades": ["AAPL"], "quotes": ["AMD", "CLDR"], "bars": ["*"]}
# Unsubscribe: {"action":"unsubscribe","trades":["VOO"],"quotes":["IBM"]}
# @SEE: https://docs.alpaca.markets/docs/real-time-stock-pricing-data
async def socket(buys):
    global websocket_connected

    stream = "wss://stream.data.alpaca.markets/v2/sip"
    async with websockets.connect(stream) as websocket:
        api_key = os.getenv("APCA_API_KEY_ID")
        api_sec = os.getenv("APCA_API_SECRET_KEY")
        auth_message = json.dumps({"action": "auth", "key": api_key, "secret": api_sec})

        await websocket.send(auth_message)

        response = await websocket.recv()

        print(f"Authentication response: {response}")

        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Invalid JSON received in the authentication response.")
            return

        if isinstance(response_data, list) and response_data[0].get("T") == "success":
            subscription_message = json.dumps(
                {
                    "action": "subscribe",
                    "trades": buys,
                    "quotes": buys,
                    "bars": ["*"],
                }
            )
            print("Authentication successful. Connected to the WebSocket.")
            websocket_connected = True
            await websocket.send(subscription_message)

            while True:
                try:
                    data = await websocket.recv()
                    print(f"Received data: {data}")
                except websockets.ConnectionClosed:
                    print("WebSocket connection closed")
                    websocket_connected = False
                    break
        else:
            print("Authentication failed.")
            websocket_connected = False
