import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta

# Replace these with your Alpaca API credentials
API_KEY = "your_api_key"
SECRET_KEY = "your_secret_key"
BASE_URL = "https://paper-api.alpaca.markets"  # Use 'https://api.alpaca.markets' for live trading

# Initialize the Alpaca API
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version="v2")


# Function to get account daily change
def get_account_daily_change(start_date, end_date):
    date_range = pd.date_range(
        start=start_date, end=end_date, freq="B"
    )  # Business days
    daily_equity = []

    for date in date_range:
        # Ensure we are checking the account at the end of the trading day
        api_time = datetime.combine(date, datetime.min.time()) + timedelta(
            hours=20
        )  # 8 PM UTC (4 PM EST)
        account = api.get_account()
        daily_equity.append((date, float(account.equity)))

    equity_df = pd.DataFrame(daily_equity, columns=["date", "equity"])
    equity_df["daily_change"] = (
        equity_df["equity"].pct_change() * 100
    )  # Percentage change

    return equity_df


# Example usage
start_date = "2023-01-01"
end_date = "2023-12-31"

daily_changes = get_account_daily_change(start_date, end_date)
print(daily_changes)
# intent is to get the daily change and save it to a dataframe in redis then we can display the data in grafana
