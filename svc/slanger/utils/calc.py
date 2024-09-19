from config import app, api

from utils import position
"""
Calc class & functions are essentially trading rules that are used to calculate the values for the order
Use the data object to get the values from the webhook and return the calculated value
"""


def profit(data):
    pos = data.get("pos")
    if pos is not False and pos is not None:
        app.logger.debug(f"PROFIT: {pos.unrealized_pl}")
        return float(pos.unrealized_pl)
    else:
        return False


# Function to get the current price of a ticker
def get_current_price(data, api):
    # Get the current bar data for the ticker
    barset = api.get_barset(data.get("symbol"), "minute", limit=1)
    bar = barset[ticker][0]
    app.loggerdebug(
        f"Time: {bar.t}, Open: {bar.o}, High: {bar.h}, Low: {bar.l}, Close: {bar.c}, Volume: {bar.v}"
    )
    return bar.c


def qty(data):
    """
    Calculate the quantity of shares to buy based on the risk value and the share price
    Logic for qty is calculated as percentage of buying_power available to trade
    Additional logic can be added to calculate the qty based on the risk value, percentage of portfolio, equal dollar investment, market cap weighting, risk mananagement, growth potential, sector allocation, etc.
    """
    buying_power = float(data["acc"].buying_power)
    
    if buying_power > 0:
        buying_power = round(buying_power * data["risk"])
        if data.get("side") == "buy":
            price = round(float(data.get("low")), 1)
        elif data.get("side") == "sell":
            price = round(float(data.get("high")), 1)
        else:
            price = round(float(data.get("open")), 1)

        qty = round(buying_power / price)
    else:
        qty = 1

    return qty


def qty_available(data, api):
    """
    Check the available quantity of shares to place an order on
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
    return qty_available



def side(data):
    """
    if empty its a buy order
    if side is both then it's a sell||buy order so we need to determine the action
    else return the side"""
    
    # if there's a position get the side
    if data.get("pos") is not False and data.get("side") is None:
        side = data.get("pos").side
        return side
    elif data.get("side") is None:
        return "buy"
    else:
        return data.get("side")


def notional(data):
    """
    Calculate the notional value of the order
    This is the total value of the order based on buying_power available to trade
    If buying_power is $1000 and risk is 0.01, then notional value is $10
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
    Helps to determine if the order is a trailing order or not this is a postprocessing order type
    """
    if data.get("trailing") == 1:
        return True
    else:
        return False


def trail_percent(data):
    """
    Set the trailing percent value
    """
    # 0.1 is the lowest it will accept
    # get current position in $ value and return 1% of that
    # @EXAMPLE: %1 of $100 is $1
    return 2


def profit_limit_price(data):
    # limit price is price * 0.98 or similar
    # Price value is coming through the webhook from tradingview so it might not be accurate to realtime price
    if data.get("action") == "buy":
        price = round(float(data.get("high")), 2)
        return price * 1.001

    elif data.get("action") == "sell":
        price = round(float(data.get("low")), 2)
        return price * 0.999


def stop_price(data):
    """s
    stop price is price * 0.98 or similar
    price is the low price of the current bar

    """
    if data.get("action") == "buy":
        price = round(float(data.get("low")), 2)
        return round(float(price * 0.999), 2)
    elif data.get("action") == "sell":
        price = round(float(data.get("high")), 2)
        return round(float(price * 1.001), 2)


def stop_limit_price(data):
    """
    stop price is price * 0.98 or similar
    price is the open price of the current
    """
    if data.get("action") == "buy":
        price = round(float(data.get("low")), 2)
        return round(float(price * 0.999), 2)
    elif data.get("action") == "sell":
        price = round(float(data.get("high")), 2)
        return round(float(price * 1.001), 2)
    

def limit_price(data: dict) -> float:
    """
    Calculate the limit price based on the action specified in the data.
    For a 'buy' action, the limit price is the low price of the current bar multiplied by 0.999.
    For a 'sell' action, the limit price is the high price of the current bar multiplied by 1.001.
    """
    action = data.get("action")
    if action == "buy":
        price = float(data.get("low", 2))
        return round(price * 0.999, 2)
    elif action == "sell":
        price = float(data.get("high", 2))
        return round(price * 1.001, 2)
    else:
        raise ValueError("Invalid action specified in data")

def risk(data):
    if data.get("risk"):
        return float(data.get("risk"))
    else:
        return 0.01


def calculate_profit(data, api):
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
            total_sell_revenue += float(order.filled_avg_price) * float(order.filled_qty)
            total_sell_quantity += float(order.filled_qty)

    return total_sell_revenue - total_buy_cost
