def profit(api, pos):
    return 1
    # take the current market value of position
    # if that is more than 1% profit then return that price/number
    #
    # value = float(pos.market_value) * 0.01
    # if value <= 0:
    #    value = 10

    # return value


def qty(api):
    """
    Calculate the quantity of shares to buy based on the risk value and the share price
    """
    # Get the available account value i.e. and divide by the risk value

    # Take share price divided by risk to get a share quantity
    return 10


def notional(api):
    # use the risk value
    return 10


def trailing(api):
    # 0.1 is the lowest it will accept
    return True


def side(api):
    # change to long short later
    return "buy"


def limit_price():
    # limit price is price * 0.98 or similar
    return 0.98


def stop_price():
    # stop price is price * 0.98 or similar
    return 0.99


def wiggle(api, data):
    return False
