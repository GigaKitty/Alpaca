def profit(data, api):
    return 1
    # take the current market value of position
    # if that is more than 1% profit then return that price/number
    #
    # value = float(pos.market_value) * 0.01
    # if value <= 0:
    #    value = 10

    # return value


def qty(data, api):
    """
    Calculate the quantity of shares to buy based on the risk value and the share price
    """
    cash = float(data["acc"].cash)
    pos = data["pos"]

    if cash > 0 and pos is not False:
        cash = round(cash * data["risk"])
        current_price = float(data["pos"].current_price)
        qty = round(cash / current_price)
    else:
        qty = 10

    return qty


def notional(data, api):
    # use the risk value
    return 10


def trailing(data, api):
    return True


def trail_percent(data, api):
    # 0.1 is the lowest it will accept
    # get current position in $ value and return 1% of that
    # @EXAMPLE: %1 of $100 is $1
    return 0.1


def side(data, api):
    # change to long short later
    return "buy"


def limit_price(data, api):
    # limit price is price * 0.98 or similar
    return 0.98


def stop_price(data, api):
    # stop price is price * 0.98 or similar
    return 0.99


def wiggle(data, api):
    return False


def risk(data, api):
    return 0.01
