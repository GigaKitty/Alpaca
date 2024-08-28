from config import app, api
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
    Logic for qty is calculated as percentage of cash available to trade
    Additional logic can be added to calculate the qty based on the risk value, percentage of portfolio, equal dollar investment, market cap weighting, risk mananagement, growth potential, sector allocation, etc.
    """
    cash = float(data["acc"].cash)
    
    if cash > 0:
        cash = round(cash * data["risk"])
        # @TODO: change to high low close dynamic based on side.
        if data.get("side") == "buy":
            price = round(float(data.get("low")), 1)
        elif data.get("side") == "sell":
            price = round(float(data.get("high")), 1)
        else:
            price = round(float(data.get("open")), 1)

        qty = round(cash / price)
    else:
        qty = 1

    return qty



def side(data):
    """
    if empty its a buy order
    if side is both then it's a sell||buy order so we need to determine the action
    else return the side"""
    if data.get("side") is None:
        return "buy"
    elif data.get("side") == "both":
        return data.get("action")
    else:
        return data.get("side")


def notional(data):
    """
    Calculate the notional value of the order
    This is the total value of the order based on cash available to trade
    If cash is $1000 and risk is 0.01, then notional value is $10
    """
    cash = float(data["acc"].cash)
    if cash > 0:
        cash = round(cash * data["risk"])
        price = round(float(data.get("low")), 1)
        return cash
    else:
        return 1


def trailing(data):
    """
    Helps to determine if the order is a trailing order or not this is a postprocessing order type
    """
    if data.get("trailing") == "False":
        return False
    else:
        return True


def trail_percent(data):
    """
    Set the trailing percent value
    """
    # 0.1 is the lowest it will accept
    # get current position in $ value and return 1% of that
    # @EXAMPLE: %1 of $100 is $1
    return 0.1


def profit_limit_price(data):
    # limit price is price * 0.98 or similar
    # Price value is coming through the webhook from tradingview so it might not be accurate to realtime price
    price = round(float(data.get("low")), 2)
    return price * 1.01


def stop_price(data):
    # stop price is price * 0.98 or similar
    price = round(float(data.get("low")), 2)
    return round(float(price * 0.99))

def stop_limit_price(data):
    # stop price is price * 0.98 or similar
    price = round(float(data.get("low")), 2)
    return round(float(price * 0.99))


def limit_price(data):
    # limit price is price * 0.98 or similar
    low = round(float(data.get("low")), 10) 
    app.logger.debug(f"low: {low}")
    limit_price = round(low * data.get("limit_price", 0.98), 10)
    app.logger.debug(f"Limit Price: {limit_price}")
    return limit_price


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
