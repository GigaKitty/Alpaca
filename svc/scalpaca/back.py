from datetime import datetime, timedelta, timezone
import pandas as pd
import alpaca_trade_api as tradeapi
import numpy as np
import logging

# Setup environment variables and initialize the Alpaca API
BASE_URL = "https://paper-api.alpaca.markets"  # Use the paper trading API for testing
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

SYMBOLS = ["UNIUSD", "DOTUSD", "SHIBUSD", "LINKUSD", "XRPUSD", "LTCUSD", "AVAXUSD"]
TIMEFRAME = "1Min"
LOOKBACK_MINUTES = 5
FEE_RATE = 0.0005
TARGET_SPREAD = 0.002
NOTIONAL_VALUE = 10

logging.basicConfig(level=logging.INFO)


def get_historical_data(symbol, start, end, timeframe):
    return api.get_crypto_bars(symbol, timeframe, start=start, end=end).df


def calculate_prices(bars):
    min_low = bars["l"].min()
    max_high = bars["h"].max()

    buying_price = min_low * 1.002  # 0.2% above the minimum low
    selling_price = max_high * 0.998  # 0.2% below the maximum high

    return buying_price, selling_price


def calculate_spread(buying_price, selling_price):
    return selling_price - buying_price


def backtest_strategy(data, symbol):
    initial_balance = 1000  # Starting balance
    balance = initial_balance
    positions = 0
    trade_log = []

    for i in range(len(data) - LOOKBACK_MINUTES):
        bars = data.iloc[i : i + LOOKBACK_MINUTES]
        buying_price, selling_price = calculate_prices(bars)
        spread = calculate_spread(buying_price, selling_price)

        if spread > (2 * FEE_RATE * buying_price + TARGET_SPREAD * buying_price):
            # Simulate buy
            positions += NOTIONAL_VALUE / buying_price
            balance -= NOTIONAL_VALUE

            # Simulate sell
            positions -= NOTIONAL_VALUE / selling_price
            balance += NOTIONAL_VALUE - (2 * FEE_RATE * NOTIONAL_VALUE)

            trade_log.append(
                {
                    "buy_price": buying_price,
                    "sell_price": selling_price,
                    "spread": spread,
                    "balance": balance,
                }
            )

    final_balance = (
        balance + positions * data["c"].iloc[-1]
    )  # Close remaining positions
    profit = final_balance - initial_balance

    return trade_log, profit


def main():
    start = datetime.now(timezone.utc) - timedelta(days=7)  # Last 7 days
    end = datetime.now(timezone.utc)

    for symbol in SYMBOLS:
        data = get_historical_data(symbol, start, end, TIMEFRAME)
        if not data.empty:
            trade_log, profit = backtest_strategy(data, symbol)
            print(f"Backtesting {symbol} completed. Profit: {profit:.2f}")
            print("Trade Log:", trade_log)
        else:
            print(f"No historical data for {symbol}")


if __name__ == "__main__":
    main()
