from datetime import datetime, timedelta, timezone
import aiohttp
import alpaca_trade_api as tradeapi
import asyncio
import logging
import os
import pandas as pd
import urllib.parse

###############################
###############################
###############################
# SETUP ENVIRONMENT VARIABLES #
###############################
###############################
###############################
"""
 Set the environment variable ENVIRONMENT_NAME to main or dev
"""
paper = True if os.getenv("ENVIRONMENT_NAME", "dev") != "main" else False

"""
Initialize the Alpaca API
If it's dev i.e. paper trading then it uses the paper trading API
"""
BASE_URL = "https://paper-api.alpaca.markets"  # Use the paper trading API for testing
HEADERS = {
    "APCA-API-KEY-ID": os.getenv("APCA_API_KEY_ID"),
    "APCA-API-SECRET-KEY": os.getenv("APCA_API_SECRET_KEY"),
}

SYMBOLS = os.getenv(
    "SYMBOLS",
    ["UNI/USD", "DOT/USD", "SHIB/USD", "LINK/USD", "XRP/USD", "LTC/USD", "AVAX/USD"],
)  # Array of cryptocurrency symbols
TIMEFRAME = os.getenv("TIMEFRAME", "1Min")
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", 5))
FEE_RATE = float(os.getenv("FEE_RATE", 0.0005))
TARGET_SPREAD = float(os.getenv("TARGET_SPREAD", 0.002))
NOTIONAL_VALUE = float(os.getenv("NOTIONAL_VALUE", 10))

logging.basicConfig(level=logging.INFO)


async def get_bar_data(session, symbol, timeframe, lookback_minutes):
    """
    Gets bar data from the crypto API.
    """
    end_time = datetime.now(timezone.utc)  # Ensure UTC timezone
    start_time = end_time - timedelta(minutes=lookback_minutes)
    symbol_encoded = urllib.parse.quote(symbol)
    url = f"https://data.alpaca.markets/v1beta3/crypto/us/bars"
    params = {
        "symbols": symbol_encoded,
        "timeframe": timeframe,
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "limit": 1000,
        "sort": "asc",
    }
    async with session.get(url, headers=HEADERS, params=params) as response:
        logging.info(f"Fetching bar data for {symbol}: {response.url}")  #
        data = await response.json()
        logging.info(f"Response for {symbol}: {data}")
        if "bars" in data and symbol in data["bars"]:
            logging.info(f"Bar data retrieved for {symbol}")
            return pd.DataFrame(data["bars"][symbol])
        else:
            logging.info(f"No bar data retrieved for {symbol}")
            return pd.DataFrame()


def calculate_prices(bars):
    """
    Figure out the buying/selling high/low
    """
    min_low = bars["l"].min()
    max_high = bars["h"].max()

    buying_price = min_low * 1.002  # 0.2% above the minimum low
    selling_price = max_high * 0.998  # 0.2% below the maximum high

    return buying_price, selling_price


def calculate_spread(buying_price, selling_price):
    return selling_price - buying_price


async def place_order(session, symbol, notional, side, limit_price):
    url = f"{BASE_URL}/v2/orders"
    order = {
        "symbol": symbol.replace("/", ""),
        "notional": notional,
        "side": side,
        "type": "limit",
        "time_in_force": "ioc",
        "limit_price": limit_price,
    }
    async with session.post(url, headers=HEADERS, json=order) as response:
        data = await response.json()
        return data


async def place_buy_order(session, symbol, buying_price):
    # Calculate the buy fee
    buy_fee = buying_price * FEE_RATE

    # Adjust buying price by adding the fee
    buying_price_adjusted = buying_price + buy_fee

    # Log the order details for debugging
    logging.info(f"Placing Buy Order for {symbol}: {buying_price_adjusted}")

    # Place a limit buy order
    buy_order = await place_order(
        session, symbol, NOTIONAL_VALUE, "buy", buying_price_adjusted
    )

    return buy_order


async def place_sell_order(session, symbol, selling_price):
    # Calculate the sell fee
    sell_fee = selling_price * FEE_RATE

    # Adjust selling price by subtracting the fee
    selling_price_adjusted = selling_price - sell_fee

    # Log the order details for debugging
    logging.info(f"Placing Sell Order for {symbol}: {selling_price_adjusted}")

    # Place a limit sell order
    sell_order = await place_order(
        session, symbol, NOTIONAL_VALUE, "sell", selling_price_adjusted
    )

    return sell_order


async def wait_for_order_fill(session, order_id):
    url = f"{BASE_URL}/v2/orders/{order_id}"
    while True:
        async with session.get(url, headers=HEADERS) as response:
            order = await response.json()
            if order["status"] == "filled":
                logging.info(f"Order {order_id} filled.")
                return True
            await asyncio.sleep(1)


async def scalping_strategy(session, symbol):
    bars = await get_bar_data(session, symbol, TIMEFRAME, LOOKBACK_MINUTES)
    if not bars.empty:
        print(f"Retrieved bar data for {symbol}:")
        print(bars)
        buying_price, selling_price = calculate_prices(bars)
        spread = calculate_spread(buying_price, selling_price)
        print(
            f"{symbol} - Buying Price: {buying_price}, Selling Price: {selling_price}, Spread: {spread}"
        )

        if spread > (2 * FEE_RATE * buying_price + TARGET_SPREAD * buying_price):
            print(
                f"{symbol} - Placing buy order as the spread is sufficient to cover fees."
            )
            buy_order = await place_buy_order(session, symbol, buying_price)

            if "id" in buy_order:
                # Wait for the buy order to fill
                await wait_for_order_fill(session, buy_order["id"])

                # Recalculate selling price to ensure spread covers fees
                bars = await get_bar_data(session, symbol, TIMEFRAME, LOOKBACK_MINUTES)
                if not bars.empty:
                    _, selling_price = calculate_prices(bars)
                    spread = calculate_spread(buying_price, selling_price)
                    logging.info(
                        f"Updated Selling Price: {selling_price}, Updated Spread: {spread}"
                    )

                    if spread > (
                        2 * FEE_RATE * buying_price + TARGET_SPREAD * buying_price
                    ):
                        print(
                            f"{symbol} - Placing sell order as the spread is sufficient to cover fees."
                        )
                        sell_order = await place_sell_order(
                            session, symbol, selling_price
                        )
                    else:
                        print(
                            f"{symbol} - Spread is not sufficient to cover fees, holding position."
                        )
                else:
                    print(f"{symbol} - No bar data retrieved after buy order.")
        else:
            print(
                f"{symbol} - Spread is not sufficient to cover fees, not placing buy order."
            )
    else:
        print(f"{symbol} - No bar data retrieved.")


async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [scalping_strategy(session, symbol) for symbol in SYMBOLS]
            await asyncio.gather(*tasks)
            await asyncio.sleep(
                60
            )  # Wait for 1 minute before running the strategy again


# Run the scalping strategy for multiple symbols
asyncio.run(main())
