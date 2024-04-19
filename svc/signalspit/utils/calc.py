def profit():
    return 1
    # take the current market value of position
    # if that is more than 1% profit then return that price/number
    #
    # value = float(pos.market_value) * 0.01
    # if value <= 0:
    #    value = 10

    # return value


def qty(data):
    """
    Calculate the quantity of shares to buy based on the risk value and the share price
    """
    cash = float(data["acc"].cash)
    pos = data["pos"]

    # @TODO: we don't need position we need the current price
    if cash > 0 and pos is not False:
        cash = round(cash * data["risk"])
        current_price = float(data["pos"].current_price)
        qty = round(cash / current_price)
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


def profit_limit_price():
    # limit price is price * 0.98 or similar
    # @TODO: this could be more intelligent to where it's
    return 0.98


def stop_price():
    # stop price is price * 0.98 or similar
    return 0.99


def limit_price():
    # limit price is price * 0.98 or similar
    return 0.98


def wiggle():
    return False


def risk():
    return 0.01
