###########
# @SEE: https://alpaca.markets/learn/automated-crypto-scalping-with-alpaca/
# Intent: Scalpaca is a simple scalping bot that trades on Alpaca's crypto API. It uses the Alpaca API to get the latest asset data and check possible trade conditions.
# Scalpaca uses the Alpaca API to get the latest asset data and check possible trade conditions. It uses the Alpaca API to get the latest asset data and check possible trade conditions.

from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import *

from alpaca.trading.requests import GetOrdersRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import os
import logging
import requests
import asyncio


#####################
#####################
#####################
# ENVIRONMENT
#####################
#####################
#####################
buy_order_price, sell_order_price = 0.00, 0.00
buy_order, sell_order = None, None
buying_price, selling_price = 0.00, 0.00
client_order_str = "scalpaca"
current_position = 0.00
current_price = 0.00
cut_loss_threshold = 0.005
diff = 5
limit = os.getenv("BAR_LIMIT", 1000)
notional_size = os.getenv("NOTIONAL_SIZE", 10000)
sort = os.getenv("SORTING", "asc")
spread = os.getenv("SPREAD", 0.00)
timeframe = os.getenv("TRADING_PAIR", "1Min")
total_fees = os.getenv("TOTAL_FEES", 0.00)
trading_fee = 0.003
trading_pair = os.getenv("TRADING_PAIR", "UNI/USD")
waitTime = 60

# ENABLE LOGGING - options, DEBUG,INFO, WARNING?
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Alpaca Trading Client
"""
 Set the environment variable ENVIRONMENT_NAME to main or dev
"""
paper = True if os.getenv("ENVIRONMENT_NAME", "dev") != "main" else False

"""
Initialize the Alpaca API
If it's dev i.e. paper trading then it uses the paper trading API
"""
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Alpaca Market Data Client
data_client = CryptoHistoricalDataClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY")
)
#####################
#####################
#####################


async def main():
    """
    Main function to get latest asset data and check possible trade conditions
    """
    while True:
        logger.info("----------------------------------------------------")
        l1 = loop.create_task(get_crypto_bar_data(trading_pair))
        # Wait for the tasks to finish
        await asyncio.wait([l1])
        # Check if any trading condition is met
        await check_condition()
        # Wait for the a certain amount of time between each bar request
        await asyncio.sleep(waitTime)


async def get_crypto_bar_data(trading_pair):
    """
    Get Crypto Bar Data from Alpaca for the last diff minutes
    """
    trading_pair_encoded = trading_pair.replace("/", "%2F")  # URL encode the slash
    url = f"https://data.alpaca.markets/v1beta3/crypto/us/bars?symbols={trading_pair_encoded}&timeframe={timeframe}&limit={limit}&sort={sort}"
    headers = {"accept": "application/json"}

    time_diff = datetime.now() - relativedelta(minutes=diff)
    logger.info(
        "Getting crypto bar data for {0} from {1}".format(trading_pair, time_diff)
    )
    # Defining Bar data request parameters
    request_params = CryptoBarsRequest(
        symbol_or_symbols=[trading_pair], timeframe=TimeFrame.Minute, start=time_diff
    )
    # Get the bar data from Alpaca
    bars_df = data_client.get_crypto_bars(request_params).df
    # Calculate the order prices
    global buying_price, selling_price, current_position
    buying_price, selling_price = calc_order_prices(bars_df)

    if len(get_positions()) > 0:
        current_position = float(json.loads(get_positions()[0].json())["qty"])

        buy_order = False
    else:
        sell_order = False
    return bars_df


def calc_order_prices(bars_df):
    global spread, total_fees, current_price
    max_high = bars_df["high"].max()
    min_low = bars_df["low"].min()
    current_price = bars_df["close"].iloc[-1]

    logger.info("Closing Price: {0}".format(current_price))
    logger.info("Min Low: {0}".format(min_low))
    logger.info("Max High: {0}".format(max_high))

    # Buying price in 0.2% below the max high
    selling_price = round(max_high * 0.998, 1)
    # Selling price in 0.2% above the min low
    buying_price = round(min_low * 1.002, 1)

    buying_fee = trading_fee * buying_price
    selling_fee = trading_fee * selling_price
    total_fees = round(buying_fee + selling_fee, 1)

    logger.info("Buying Price: {0}".format(buying_price))
    logger.info("Selling Price: {0}".format(selling_price))
    logger.info("Total Fees: {0}".format(total_fees))

    # Calculate the spread
    spread = round(selling_price - buying_price, 1)

    logger.info(
        "Spread that can be captured with buying and selling prices: {0}".format(spread)
    )

    return buying_price, selling_price


def get_positions():
    positions = api.get_all_positions()

    return positions


def get_open_orders():
    orders = api.get_orders(trading_pair, OrderStatus.NEW)

    num_orders = len(orders)
    logger.info("Number of open orders: {0}".format(num_orders))

    global buy_order, sell_order

    for i in range(len(orders)):
        ord = json.loads(orders[i].json())
        logger.info(
            "Order type: {0} Order side: {1} Order notional: {2}  Order Symbol: {3} Order Price: {4}".format(
                ord["type"],
                ord["side"],
                ord["notional"],
                ord["symbol"],
                ord["limit_price"],
            )
        )
        if ord["side"] == "buy":
            buy_order = True
        if ord["side"] == "sell":
            sell_order = True

    return num_orders


async def post_alpaca_order(buy_price, sell_price, side):
    """
    Post an order to Alpaca
    """
    global buy_order_price, sell_order_price, buy_order, sell_order
    try:
        if side == "buy":
            # print("Buying at: {0}".format(price))
            limit_order_data = LimitOrderRequest(
                symbol=trading_pair,
                limit_price=buy_price,
                notional=notional_size,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
            buy_limit_order = api.submit_order(order_data=limit_order_data)
            buy_order_price = buy_price
            sell_order_price = sell_price
            # buy_order = True
            logger.info(
                "Buy Limit Order placed for {0} at : {1}".format(
                    trading_pair, buy_limit_order.limit_price
                )
            )
            return buy_limit_order
        else:
            limit_order_data = LimitOrderRequest(
                symbol=trading_pair,
                limit_price=sell_price,
                notional=notional_size,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
            )
            sell_limit_order = api.submit_order(order_data=limit_order_data)
            #            sell_order_price = sell_price
            buy_order_price = buy_price
            # sell_order = True
            logger.info(
                "Sell Limit Order placed for {0} at : {1}".format(
                    trading_pair, sell_limit_order.limit_price
                )
            )
            return sell_limit_order

    except Exception as e:
        logger.exception("There was an issue posting order to Alpaca: {0}".format(e))
        return False


async def check_condition():
    """
    Check the market conditions to see what limit orders to place

    Strategy:
    - Only consider placing orders if the spread is greater than the total fees after fees are taken into account
    - If the spread is greater than the total fees and we do not have a position, then place a buy order
    - If the spread is greater than the total fees and we have a position, then place a sell order
    - If we do not have a position, a buy order is in place and the current price is more than price we would have sold at, then close the buy limit order
    - If we do have a position, a sell order is in place and the current price is less than price we would have bought at, then close the sell limit order

    """
    global buy_order, sell_order, current_position, current_price, buying_price, selling_price, spread, total_fees, buy_order_price, sell_order_price
    get_open_orders()
    logger.info("Current Position is: {0}".format(current_position))
    logger.info("Buy Order status: {0}".format(buy_order))
    logger.info("Sell Order status: {0}".format(sell_order))
    logger.info("Buy_order_price: {0}".format(buy_order_price))
    logger.info("Sell_order_price: {0}".format(sell_order_price))
    # If the spread is less than the fees, do not place an order
    if spread < total_fees:
        logger.info(
            "Spread is less than total fees, Not a profitable opportunity to trade"
        )
    else:
        # If we do not have a position, there are no open orders and spread is greater than the total fees, place a limit buy order at the buying price
        if (
            current_position <= 0.01
            and (not buy_order)
            and current_price > buying_price
        ):
            buy_limit_order = await post_alpaca_order(
                buying_price, selling_price, "buy"
            )
            sell_order = False
            if (
                buy_limit_order
            ):  # check some attribute of buy_order to see if it was successful
                logger.info("Placed buy limit order at {0}".format(buying_price))

        # if we have a position, no open orders and the spread that can be captured is greater than fees, place a limit sell order at the sell_order_price
        if (
            current_position >= 0.01
            and (not sell_order)
            and current_price < sell_order_price
        ):
            sell_limit_order = await post_alpaca_order(
                buying_price, selling_price, "sell"
            )
            buy_order = False
            if sell_limit_order:
                logger.info("Placed sell limit order at {0}".format(selling_price))

        # Cutting losses
        # If we have do not have a position, an open buy order and the current price is above the selling price, cancel the buy limit order
        logger.info(
            "Threshold price to cancel any buy limit order: {0}".format(
                sell_order_price * (1 + cut_loss_threshold)
            )
        )
        if (
            current_position <= 0.01
            and buy_order
            and current_price > (sell_order_price * (1 + cut_loss_threshold))
        ):
            # api.cancel_orders()
            buy_order = False
            logger.info(
                "Current price > Selling price. Closing Buy Limit Order, will place again in next check"
            )
        # If we have do have a position and an open sell order and current price is below the buying price, cancel the sell limit order
        logger.info(
            "Threshold price to cancel any sell limit order: {0}".format(
                buy_order_price * (1 - cut_loss_threshold)
            )
        )
        if (
            current_position >= 0.01
            and sell_order
            and current_price < (buy_order_price * (1 - cut_loss_threshold))
        ):
            # api.cancel_orders()
            sell_order = False
            logger.info(
                "Current price < buying price. Closing Sell Limit Order, will place again in next check"
            )


def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.info("Shutting down...")
    asyncio.create_task(shutdown(loop))


# Run the main function
loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
loop.run_until_complete(main())
