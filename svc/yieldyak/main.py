from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time, timedelta
from google.oauth2.service_account import Credentials
from alpaca.trading.enums import ActivityType, QueryOrderStatus
from googleapiclient.discovery import build
from pytz import timezone
import asyncio
import gspread
import requests
import os
from time import sleep

environment = os.getenv("ENVIRONMENT", "dev")
paper = True if environment != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)


tz = timezone("America/New_York")
today = datetime.now(tz).date().isoformat()

if paper is False:
    BASE_URL = "https://api.alpaca.markets"

else:
    BASE_URL = "https://paper-api.alpaca.markets"

DATA_URL = "https://data.alpaca.markets/v2"

headers = {
    "APCA-API-KEY-ID": os.getenv("APCA_API_KEY_ID"),
    "APCA-API-SECRET-KEY": os.getenv("APCA_API_SECRET_KEY"),
}

# Google Sheets setup
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]
SERVICE_ACCOUNT_FILE = "/app/.credentials.json"
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
spreadsheet = gc.open("yieldyak")
worksheet = spreadsheet.worksheet(os.getenv("ENVIRONMENT", "dev"))
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)


def add_google_calendar_event(summary, description, start_time, end_time):
    calendar_service = build("calendar", "v3", credentials=credentials)

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time.astimezone(
                timezone("America/Los_Angeles")
            ).isoformat(),
            "timeZone": "America/Los_Angeles",
        },
        "end": {
            "dateTime": end_time.astimezone(
                timezone("America/Los_Angeles")
            ).isoformat(),
            "timeZone": "America/Los_Angeles",
        },
    }
    # Add logging to verify the values
    print(f"Adding event to calendar ID: {GOOGLE_CALENDAR_ID}")
    print(f"Event details: {event}")

    try:
        return (
            calendar_service.events()
            .insert(calendarId=GOOGLE_CALENDAR_ID, body=event)
            .execute()
        )
    except Exception:
        raise


# Function to get traded symbols for the day
def get_all_traded_symbols():
    url = f"{BASE_URL}/v2/account/activities/FILL?date={today}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        activities = response.json()
        # Extract unique symbols
        symbols = {activity["symbol"] for activity in activities}
        print(f"Traded Symbols for {today}: {sorted(symbols)}")
    else:
        print(f"Error fetching activities: {response.content}")

    return sorted(symbols)


# Function to get account activities for a specific ticker
# Function to get account activities for a specific ticker
def get_ticker_daily_pl(ticker):
    # New york timezone
    today = datetime.now(tz).date().isoformat()
    url = f"{BASE_URL}/v2/account/activities/FILL?date={today}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        activities = response.json()
        ticker_activities = [
            activity for activity in activities if activity["symbol"] == ticker
        ]

        # Calculate daily P/L for the ticker
        daily_pl = sum(
            float(activity["price"]) * float(activity["qty"])
            for activity in ticker_activities
        )

        # Fetch the initial value of the ticker for the day
        initial_value = get_initial_value(ticker, today)

        # Calculate daily P/L percentage
        daily_pl_percent = (daily_pl / initial_value) * 100 if initial_value != 0 else 0

        # Print the results
        print(f"Ticker: {ticker}")
        print(f"Daily P/L: {daily_pl}")
        print(f"Daily P/L %: {daily_pl_percent:.2f}%")

        return {
            "ticker": ticker,
            "daily_pl": daily_pl,
            "daily_pl_percent": daily_pl_percent,
        }
    else:
        print(f"Error fetching activities for ticker {ticker}: {response.content}")
        return None


# Function to get the initial value of the ticker for the day
def get_initial_value(ticker, date):
    url = f"{BASE_URL}/v2/stocks/{ticker}/bars?start={date}&end={date}&timeframe=1Day"
    response = requests.get(url, headers=headers)

    print(f"response: {response}")
    if response.status_code == 200:
        bars = response.json().get("bars", [])
        if bars:
            return float(bars[0]["o"])  # 'o' is the opening price
        else:
            print(f"No bars data available for ticker {ticker} on {date}")
            return 0.0
    elif response.status_code == 404:
        print(f"Ticker {ticker} not found on {date}")
        return 0.0
    else:
        print(f"Error fetching initial value for ticker {ticker}: {response.content}")
        return 0.0


# Function to get open position P/L
def get_open_position(ticker):
    url = f"{BASE_URL}/v2/positions/{ticker}"
    response = requests.get(url, headers=headers)
    print(f"response: {response.json()}")
    if response.status_code == 200:
        position = response.json()
        return position


def get_open_price(ticker):
    today = datetime.now(tz).date().isoformat()
    url = f"{DATA_URL}/stocks/{ticker}/bars?start={today}&end={today}&timeframe=1Day"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        bars = response.json().get("bars", [])
        if bars:
            return float(bars[0]["o"])  # Open price of the first bar of the day
        else:
            print(f"No data available for {ticker} on {today}.")
            return None
    else:
        print(f"Error fetching market data for {ticker}: {response.content}")
        return None


def get_unrealized_intraday_pl(ticker):
    # Fetch position details
    position_url = f"{BASE_URL}/v2/positions/{ticker}"
    response = requests.get(position_url, headers=headers)

    if response.status_code == 200:
        position = response.json()
        qty = float(position["qty"])
        avg_entry_price = float(position["avg_entry_price"])

        # Fetch the opening price of the day
        open_price = get_open_price(ticker)

        if open_price is not None:
            # Calculate intraday P/L based on opening price
            unrealized_intraday_pl = (open_price - avg_entry_price) * qty
            print(f"Ticker: {ticker}")
            print(f"Quantity: {qty}")
            print(f"Average Entry Price: {avg_entry_price}")
            print(f"Opening Price: {open_price}")
            print(
                f"Unrealized Intraday P/L (from start of the day): {unrealized_intraday_pl:.2f}"
            )
    else:
        print(f"Error fetching position for {ticker}: {response.content}")


# Function to get account information including daily P/L
def get_account_dailys():
    # Endpoint to get account details
    url = f"{BASE_URL}/v2/account"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        account = response.json()
        try:
            account["daily_pl"] = float(account["equity"]) - float(
                account["last_equity"]
            )
            account["daily_pl_percent"] = (
                account["daily_pl"] / float(account["last_equity"])
            ) * 100
        except Exception as e:
            print(f"Error calculating daily P/L: {e}")
    else:
        print(f"Error fetching account details: {response.content}")
    print(account)
    return account


# Function to get closed position P/L
def get_closed_positions(ticker):
    today = datetime.now().date().isoformat()
    url = f"{BASE_URL}/v2/account/activities/FILL?date={today}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        activities = response.json()
        print(activities)
        return
        ticker_activities = [
            activity for activity in activities if activity["symbol"] == ticker
        ]

        # Calculate the total realized P/L for today
        total_pl = sum(
            float(activity.get("cum_qty", 0)) * float(activity.get("price", 0))
            for activity in ticker_activities
        )

        if ticker_activities:
            print(f"Closed Position Activities for {ticker}:")
            for activity in ticker_activities:
                print(
                    f"Activity: {activity['side']} {activity['qty']} at {activity['price']} on {activity['transaction_time']}"
                )
            print(f"Total Realized P/L for {ticker} Today: {total_pl:.2f}")
        else:
            print(f"No closed positions for {ticker} today.")
    else:
        print(f"Error fetching activities for {ticker}: {response.content}")


def calculate_total_pl(ticker, api):
    try:
        position = api.get_open_position(ticker)
        print(f"Open Position for {ticker}:")
        print(f"Current Price: {position.current_price}")
        print(f"Unrealized Intraday P/L: {position.unrealized_intraday_pl}")
        print(f"Percentage P/L: {position.unrealized_intraday_plpc * 100:.2f}%")
    except Exception as e:
        # If the position is not open, it might be closed. Let's fetch today's closed trades.
        print(f"No open position for {ticker}. Checking closed positions...")

    # Get today's date
    today = datetime.now().date()

    # Create request object for account activities
    request_params = GetAccountActivitiesRequest(
        activity_types=[ActivityType.FILL], date=today
    )

    try:
        # Fetch account activities using the correct method
        activities = trading_client.get_account_activities(request_params)

        # Filter activities for the specific ticker
        ticker_activities = [
            activity for activity in activities if activity.symbol == ticker
        ]

        # Calculate the total realized P/L for today
        total_pl = sum(
            float(activity.realized_pl or 0) for activity in ticker_activities
        )

        if ticker_activities:
            print(f"Closed Position Activities for {ticker}:")
            for activity in ticker_activities:
                print(
                    f"Activity: {activity.side} {activity.qty} at {activity.price} on {activity.transaction_time}"
                )
            print(f"Total Realized P/L for {ticker} Today: {total_pl:.2f}")
        else:
            print(f"No closed positions for {ticker} today.")
    except Exception as e:
        print(f"Error fetching activities for {ticker}: {e}")
    # # Fetch all orders for the given symbol
    # current_date = datetime.now().date()

    # # Set the start time to 6 AM
    # start_time = datetime.combine(current_date, time(6, 0))

    # # Set the end time to 5 PM
    # end_time = datetime.combine(current_date, time(17, 0))
    # orders_request = GetOrdersRequest(
    #     status='all',
    #     symbols=[symbol],
    #     after=start_time.isoformat(),
    #     until=end_time.isoformat()
    # )
    # orders_request = GetOrdersRequest(
    #     status='all',
    #     symbols=[symbol]
    # )
    # orders = api.get_orders(filter=orders_request)
    # # Initialize position and cash variables
    # position = 0
    # cash = 0

    # # Calculate P/L
    # for order in orders:
    #     if float(order.filled_qty) > 0:  # Check if the order is filled
    #         quantity = float(order.filled_qty)
    #         price = float(order.filled_avg_price)
    #         if order.side == 'buy':
    #             position += quantity
    #             cash -= price * quantity
    #         elif order.side == 'sell':
    #             position -= quantity
    #             cash += price * quantity

    # # Assuming at EOD, all positions are closed at the last traded price
    # if position != 0:
    #     data_client = StockHistoricalDataClient(api_key=os.getenv("APCA_API_KEY_ID"), secret_key=os.getenv("APCA_API_SECRET_KEY"))
    #     trade_request = StockLatestTradeRequest(symbol_or_symbols =symbol)
    #     last_trade  = data_client.get_stock_latest_trade(trade_request)
    #     eod_price = float(last_trade[symbol].price)  # Extract the price from the dictionary
    #     eod_value = position * eod_price
    # else:
    #     eod_value = 0

    # # Final P/L
    # total_pl = cash + eod_value

    # return total_pl


def format_data_as_table(data):
    table = "<table style='border-collapse: collapse;'>"
    for row in data:
        table += "<tr>"
        for cell in row:
            if isinstance(cell, (int, float)):
                cell = round(cell, 1)
                if cell < 0:
                    table += (
                        f"<td style='padding: 5px; text-align: right;'>🔴 {cell}</td>"
                    )
                elif cell > 0:
                    table += (
                        f"<td style='padding: 5px; text-align: right;'>🟢 {cell}</td>"
                    )
            else:
                table += f"<td style='padding: 5px; text-align: right;'>{cell}</td>"
        table += "</tr>"
    table += "</table>"
    return table


def calculate_daily_pl(ticker):
    orders = get_orders_for_ticker(ticker)
    if not orders:
        return 0.0

    total_pl = 0.0
    for order in orders:
        if (
            order["status"] == "filled"
            and order["filled_qty"] != None
            and order["filled_avg_price"] != None
        ):
            side = order["side"]
            qty = float(order["filled_qty"])
            filled_avg_price = float(order["filled_avg_price"])
            filled_at = order["filled_at"]

            print(f"{filled_at} {qty} {ticker} at {filled_avg_price}")
            if side == "buy":
                total_pl -= qty * filled_avg_price
            elif side == "sell":
                total_pl += qty * filled_avg_price
    print(f"∑ P/L for {ticker}: {total_pl}")
    return total_pl


def get_orders_for_ticker(ticker):
    all_orders = []
    limit = 500  # Maximum limit per request
    today = datetime.now(tz).date()
    start_date = datetime(today.year, 1, 1).date()  # January 1st of the current year
    end_date = today.isoformat()  # Current date
    after = start_date.isoformat()

    while True:
        # API request parameters
        params = {
            "symbols": ticker,
            "status": "all",  # Fetch all statuses: 'open', 'closed', 'canceled'
            "after": after,
            "direction": "asc",  # Sort in ascending order
            "until": end_date,
            "limit": limit,
        }

        url = f"{BASE_URL}/v2/orders"
        response = requests.get(url, headers=headers, params=params)
        sleep(0.5)  # Sleep for 0.5 seconds to avoid rate limiting
        if response.status_code != 200:
            print(f"Error fetching orders: {response.content}")
            break

        orders = response.json()
        if not orders:
            break

        all_orders.extend(orders)

        after = orders[-1][
            "submitted_at"
        ]  # Update 'after' to the last order's submission time
    return all_orders


def add_orders_to_sheet(orders, sheet_name):
    try:
        sheet = gc.open("Your Google Spreadsheet Name").worksheet(
            sheet_name + environment
        )
    except gspread.exceptions.WorksheetNotFound:
        sheet = gc.open("Your Google Spreadsheet Name").add_worksheet(
            title=sheet_name, rows="1000", cols="20"
        )

    # Add header if the sheet is empty
    if sheet.row_count == 0:
        sheet.append_row(
            [
                "id",
                "client_order_id",
                "created_at",
                "updated_at",
                "submitted_at",
                "filled_at",
                "expired_at",
                "canceled_at",
                "failed_at",
                "replaced_at",
                "replaced_by",
                "replaces",
                "asset_id",
                "symbol",
                "asset_class",
                "notional",
                "qty",
                "filled_qty",
                "filled_avg_price",
                "order_class",
                "order_type",
                "type",
                "side",
                "position_intent",
                "time_in_force",
                "limit_price",
                "stop_price",
                "status",
                "extended_hours",
                "legs",
                "trail_percent",
                "trail_price",
                "hwm",
                "subtag",
                "source",
            ]
        )

    existing_order_ids = sheet.col_values(1)  # Assuming 'id' is in the first column

    for order in orders:
        sheet.append_row(
            [
                order.get("id"),
                order.get("client_order_id"),
                order.get("created_at"),
                order.get("updated_at"),
                order.get("submitted_at"),
                order.get("filled_at"),
                order.get("expired_at"),
                order.get("canceled_at"),
                order.get("failed_at"),
                order.get("replaced_at"),
                order.get("replaced_by"),
                order.get("replaces"),
                order.get("asset_id"),
                order.get("symbol"),
                order.get("asset_class"),
                order.get("notional"),
                order.get("qty"),
                order.get("filled_qty"),
                order.get("filled_avg_price"),
                order.get("order_class"),
                order.get("order_type"),
                order.get("type"),
                order.get("side"),
                order.get("position_intent"),
                order.get("time_in_force"),
                order.get("limit_price"),
                order.get("stop_price"),
                order.get("status"),
                order.get("extended_hours"),
                order.get("legs"),
                order.get("trail_percent"),
                order.get("trail_price"),
                order.get("hwm"),
                order.get("subtag"),
                order.get("source"),
            ]
        )


async def main():
    symbols = get_all_traded_symbols()
    account = get_account_dailys()  # Get daily P/L for the account
    account_daily_pl = round(account["daily_pl"], 2)
    account_daily_pl_percent = round(account["daily_pl_percent"], 2)

    data = []
    for symbol in symbols:
        # get all orders for the symbol
        if symbol == "ZGN":

            orders = get_orders_for_ticker(symbol)
            add_orders_to_sheet(orders, symbol)

            # get_unrealized_intraday_pl(symbol)
            # pos = get_open_position(symbol)
            # if pos is not None and pos["unrealized_intraday_pl"] is not None:
            #    unrealized_intraday_pl = pos["unrealized_intraday_pl"]
            #    change_today = pos["change_today"]
            #    data.append([symbol, unrealized_intraday_pl, change_today])

            # Spreadsheets
            # data.append(["Total", account_daily_pl])
            # worksheet = spreadsheet.worksheet(os.getenv("ENVIRONMENT", "dev") + symbol)
            # worksheet.update(range_name='A1', values=data)  # Update the Google Sheet with the data

    # Add Google Calendar event
    table = format_data_as_table(data)
    start_time = datetime.now(tz).replace(hour=16, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(
        minutes=15
    )  # Set the event duration to 15 minutes

    if account_daily_pl >= 0:
        summary = f"💚🦙{environment} +🤑{account_daily_pl} {account_daily_pl_percent}%"
    else:
        summary = f"🩸🦙{environment} -😭{account_daily_pl} {account_daily_pl_percent}%"

    description = f"Daily P/L for all symbols:\nonly adds open positions and traded positions for the day not existing or closed\n\n{table}"

    add_google_calendar_event(summary, description, start_time, end_time)


def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main,
        "cron",
        day_of_week="mon-fri",
        hour=16,
        minute=00,
        timezone="America/New_York",
    )
    scheduler.start()
    try:
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    run_scheduler()
