from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pytz import timezone
import asyncio
import gspread
import os


environment=os.getenv('ENVIRONMENT', 'dev')
paper = True if environment != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = '/app/.credentials.json'
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
spreadsheet = gc.open('yieldyak')
worksheet = spreadsheet.worksheet(os.getenv('ENVIRONMENT', 'dev'))
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)


def add_google_calendar_event(summary, description, start_time, end_time):
    calendar_service = build('calendar', 'v3', credentials=credentials)

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
    }
     # Add logging to verify the values
    print(f"Adding event to calendar ID: {GOOGLE_CALENDAR_ID}")
    print(f"Event details: {event}")

    try:
        return calendar_service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
    except Exception:
        raise

def get_all_traded_symbols(api):
    # Fetch all orders for today
    orders_request = GetOrdersRequest(status='all', limit=500, after=(datetime.now() - timedelta(days=1)).isoformat())
    orders = api.get_orders(filter=orders_request)
    
    # Extract unique symbols from orders
    symbols = set(order.symbol for order in orders)
    # return a sorted list of symbols
    return sorted(symbols)



def calculate_total_pl(symbol, api):    
    # Fetch all orders for the given symbol
    current_date = datetime.now().date()

    # Set the start time to 6 AM
    start_time = datetime.combine(current_date, time(6, 0))

    # Set the end time to 5 PM
    end_time = datetime.combine(current_date, time(17, 0))
    orders_request = GetOrdersRequest(
        status='all',
        symbols=[symbol],
        after=start_time.isoformat(),
        until=end_time.isoformat()
    )
    orders_request = GetOrdersRequest(
        status='all',
        symbols=[symbol]
    )
    orders = api.get_orders(filter=orders_request)
    # Initialize position and cash variables
    position = 0
    cash = 0

    # Calculate P/L
    for order in orders:
        if float(order.filled_qty) > 0:  # Check if the order is filled
            quantity = float(order.filled_qty)
            price = float(order.filled_avg_price)
            if order.side == 'buy':
                position += quantity
                cash -= price * quantity
            elif order.side == 'sell':
                position -= quantity
                cash += price * quantity

    # Assuming at EOD, all positions are closed at the last traded price
    if position != 0:
        data_client = StockHistoricalDataClient(api_key=os.getenv("APCA_API_KEY_ID"), secret_key=os.getenv("APCA_API_SECRET_KEY"))
        trade_request = StockLatestTradeRequest(symbol_or_symbols =symbol)
        last_trade  = data_client.get_stock_latest_trade(trade_request)
        eod_price = float(last_trade[symbol].price)  # Extract the price from the dictionary
        eod_value = position * eod_price
    else:
        eod_value = 0

    # Final P/L
    total_pl = cash + eod_value

    return total_pl


def format_data_as_table(data):
    table = ""
    for row in data:
        table += "\t".join(map(str, row)) + "\n"
    return table

async def main():
    print("Calculating total P/L for all symbols")
    print(f"timestamp: {datetime.now()}")
    print(f"Symbols: {symbols}")
    total_pl_all_symbols = 0  # Initialize total P/L for all symbols

    # Prepare data for Google Sheets
    data = [["Symbol", "P/L"]]
    for symbol in symbols:
        pl = calculate_total_pl(symbol, api)
        print(f"Total P/L for {symbol}: {pl}")
        total_pl_all_symbols += pl  # Accumulate total P/L
        data.append([symbol, pl])
 
    data.append(["Total", total_pl_all_symbols])
    worksheet.update(range_name='A1', values=data)  # Update the Google Sheet with the data

    print(f"Total P/L for all symbols: {total_pl_all_symbols}")
    
    # Add Google Calendar event
    table = format_data_as_table(data)

    start_time = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=15)  # Set the event duration to 15 minutes
    if total_pl_all_symbols >= 0:
        summary = f"💚Daily P/L Report {environment} +🤑{total_pl_all_symbols}"
    else:
        summary = f"😡Daily P/L Report {environment} -😭{total_pl_all_symbols}"

    description = f"Daily P/L for all symbols:\n\n{table}"

    add_google_calendar_event(summary, description, start_time, end_time)

def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main,
        "cron",
        day_of_week="mon-fri",
        hour=18,
        minute=00,
        timezone="America/New_York",
    )
    scheduler.start()
    print("Scheduler started")
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

symbols = get_all_traded_symbols(api)

if __name__ == "__main__":
    run_scheduler()




