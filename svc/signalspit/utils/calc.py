def profit():
    return 1
    # take the current market value of position
    # if that is more than 1% profit then return that price/number
    #
    # value = float(pos.market_value) * 0.01
    # if value <= 0:
    #    value = 10

    # return value


# Function to get the current price of a ticker
def get_current_price(data, api):
    # Get the current bar data for the ticker
    barset = api.get_barset(data.get("symbol"), "minute", limit=1)
    bar = barset[ticker][0]
    print(
        f"Time: {bar.t}, Open: {bar.o}, High: {bar.h}, Low: {bar.l}, Close: {bar.c}, Volume: {bar.v}"
    )
    return bar.c


def qty(data):
    """
    Calculate the quantity of shares to buy based on the risk value and the share price
    """
    cash = float(data["acc"].cash)

    print(cash)
    if cash > 0:
        cash = round(cash * data["risk"])
        # @TODO: change to high low close dynamic based on side.
        price = round(float(data.get("low")), 2)

        qty = round(cash / price)
    else:
        qty = 1

    return qty


def notional():
    # use the risk value
    return 10


def trailing():
    return True


def trail_percent():
    # 0.1 is the lowest it will accept
    # get current position in $ value and return 1% of that
    # @EXAMPLE: %1 of $100 is $1
    return 0.1


def side():
    # change to long short later
    return "buy"


def profit_limit_price(data):
    # limit price is price * 0.98 or similar
    # Price value is coming through the webhook from tradingview so it might not be accurate to realtime price
    price = round(float(data.get("low")), 2)
    return price * 1.01


def stop_price(data):
    # stop price is price * 0.98 or similar
    price = round(float(data.get("low")), 2)
    return round(float(price * 0.99))


def limit_price(data):
    # limit price is price * 0.98 or similar
    price = round(float(data.get("low")), 2)
    return round(float(price * 0.98))


def wiggle():
    return False


def risk():
    return 0.01
