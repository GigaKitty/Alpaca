from config import app, api
import os
from utils import position

"""
Calc class & functions are essentially trading rules that are used to calculate the values for the order
Use the data object to get the values from the webhook and return the calculated value
"""


def profit(data):
    """
    - Calculate the profit based on the data received from the webhook
    - If the data contains a position, return the profit in the position
    - If the data does not contain a position, return 0
    - Return the calculated profit
    """
    pos = data.get("pos")
    if pos is not False and pos is not None:
        app.logger.debug(f"PROFIT: {pos.unrealized_pl}")
        return float(pos.unrealized_pl)
    else:
        return False


def qty(data):
    """
    - If qty is set statically in the reqeust then keep that value
    - If qty is not set, calculate the quantity based on the data buying power
    - Else return base
    - at the end we add base to the qty to ensure we have a an extra reserve of 10 shares to let them run.
    - Therefore the minimum qty will be 20 shares so gotta have that 💰💸🪙
    """
    buying_power = float(data["acc"].buying_power)
    base = g.data.get("base")
    if data.get("qty") is not None:
        return round(data.get("qty"))
    elif buying_power > 0 and data.get("price") is not None:
        market_value = round(buying_power * data["risk"]) # Calculate the market value based on the account buying power and risk
        divisible = round(market_value / float(data.get("price"))) # Round to the nearest whole number so we know how many shares to allocate
        qty = base * round(divisible / base) # Round to the nearest base number likely 10
        if qty >= base:
            return qty + base
        else:
            return base + base
    else:
        return base + base


def qty_available(data, api):
    """
    - Calculate the quantity available based on the data received from the webhook
    - If the data contains a position, return the quantity available in the position
    - If the data does not contain a position, return the quantity available in the account
    - Return the quantity available
    """
    qty_available = data.get("qty")
    if position.get_position(data, api) is not False:
        try:
            pos = position.get_position(data, api)
            qty_available = pos.qty_available
        except ValueError:
            # Handle the case where the string does not represent a number
            app.logger.error(f"Error: is not a valid number.")
            return None
    app.logger.debug(f"Quantity Available: {qty_available}")

    if qty_available is None:
        return 0

    return qty_available


def side(data):
    """
    - Determine the side of the order based on the data received from the webhook
    - If the data contains a position and the side is not specified, return the side of the position
    - If the data does not contain a side, return 'buy'
    - Return the side of the order
    - The side of the order can be 'buy' or 'sell'
    - The side of the order is used to determine if the order is a buy order or a sell order
    """
    if data.get("pos") is not False and data.get("side") is None:
        side = data.get("pos").side
        return side
    elif data.get("side") is None:
        return "buy"
    else:
        return data.get("side")


def notional(data):
    """
    - Calculate the notional value based on the data received from the webhook
    - If the data contains a notional value, return the notional value
    - If the data does not contain a notional value, return a default notional value of 1000
    - The notional value is used to determine the total value of the order
    - The notional value is calculated as the quantity of shares multiplied by the price of the shares
    - Return the calculated notional value
    """
    buying_power = float(data["acc"].buying_power)
    if buying_power > 0:
        buying_power = round(buying_power * data["risk"])
        price = round(float(data.get("low")), 1)
        return buying_power
    else:
        return 1


def trailing(data):
    """
    - Check if the trailing value is set to 1
    - If the trailing value is set to 1, return True
    - If the trailing value is not set to 1, return False
    - The trailing value is used to determine if the order should have a trailing order after the priamry order submitted
    """
    if data.get("trailing") == 1:
        return True
    else:
        return False


def trail_percent(data: dict) -> float:
    """
    Set the trailing percent value
    """
    # 0.1 is the lowest it will accept
    # get current position in $ value and return 1% of that
    # @EXAMPLE: %1 of $100 is $1
    return 0.1


def profit_limit_price(data: dict) -> float:
    # limit price is price * 0.98 or similar
    # Price value is coming through the webhook from tradingview so it might not be accurate to realtime price
    if data.get("action") == "buy":
        price = round(float(data.get("high")), 2)
        return round(float(price * data.get("profit_limit_price_buy", 1.001)), 2)

    elif data.get("action") == "sell":
        price = round(float(data.get("low")), 2)
        return round(float(price * data.get("profit_limit_price_sell", 0.999)), 2)


def stop_price(data: dict) -> float:
    """
    - Calculate the stop price based on the action specified in the data.
    - For a 'buy' action, the stop price is the low price of the current bar minus 0.02.
    - For a 'sell' action, the stop price is the high price of the current bar plus 0.02.
    - Return the calculated stop price.
    """
    if data.get("action") == "buy":
        price = round(float(data.get("low")), 2)
        return round(float(price * data.get("stop_price_buy", 0.999)), 2)
    elif data.get("action") == "sell":
        price = round(float(data.get("high")), 2)
        return round(float(price * data.get("stop_price_sell", 1.001)), 2)


def stop_limit_price(data: dict) -> float:
    """
    - Calculate the stop limit price based on the action specified in the data.
    - For a 'buy' action, the stop limit price is the low price of the current bar multiplied by 0.999.
    - For a 'sell' action, the stop limit price is the high price of the current bar multiplied by 1.001.
    - Return the calculated stop limit price
    """
    if data.get("action") == "buy":
        price = round(float(data.get("low")), 2)
        return round(float(price * data.get("stop_limit_price_buy", 0.999)), 2)
    elif data.get("action") == "sell":
        price = round(float(data.get("high")), 2)
        return round(float(price * data.get("stop_limit_price_sell", 1.001)), 2)


def limit_price(data: dict) -> float:
    """
    - Calculate the limit price based on the action specified in the data.
    - For a 'buy' action, the limit price is the low price of the current bar multiplied by 0.999.
    - For a 'sell' action, the limit price is the high price of the current bar multiplied by 1.001.
    """
    action = data.get("action")
    if action == "buy":
        price = float(data.get("low", 2))
        return round(price * data.get("limit_price_buy", 0.999), 2)
    elif action == "sell":
        price = float(data.get("high", 2))
        return round(price * data.get("limit_price_sell", 1.001), 2)
    else:
        raise ValueError("Invalid action specified in data")


def risk(data):
    """
    - Calculate the risk value based on the data received from the webhook
    - If the data contains a risk value, return the risk value
    - If the data does not contain a risk value, return a default risk value of 0.01
    """
    if data.get("risk"):
        return float(data.get("risk", 0.01))
    elif os.getenv("RISK"):
        return float(os.getenv("RISK", 0.01))
    else:
        return 0.01


def calculate_profit(data, api):
    """
    - Calculate the profit made from the orders placed for a specific symbol
    - Get all the orders for the symbol
    - Calculate the total buy cost and total sell revenue
    - Return the profit made from the orders
    """
    symbol = data.get("symbol")
    orders = api.get_orders(symbol=[symbol])

    total_buy_cost = 0
    total_buy_quantity = 0
    total_sell_revenue = 0
    total_sell_quantity = 0

    for order in orders:
        if order.side == OrderSide.BUY and order.status == OrderStatus.FILLED:
            total_buy_cost += float(order.filled_avg_price) * float(order.filled_qty)
            total_buy_quantity += float(order.filled_qty)
        elif order.side == OrderSide.SELL and order.status == OrderStatus.FILLED:
            total_sell_revenue += float(order.filled_avg_price) * float(
                order.filled_qty
            )
            total_sell_quantity += float(order.filled_qty)

    return total_sell_revenue - total_buy_cost
