import math
import string


############################################################
# Gets currently open position for ticker
def get_position(data, api):
    """
    Checks the position of the current ticker
    """
    try:
        position = api.get_open_position(data.get("ticker"))
        if position is None:
            return False
        else:
            return position
    except Exception as e:
        return False


def get_current_price(data, api):
    pos = get_position(data, api)
    if pos is not False:
        return float(pos.current_price)


def qty_available(data, api):
    """
    Check the available quantity of shares to place a trailling order on
    """

    qty_available = data.get("qty")

    try:
        pos = get_position(data, api)
        print(pos.qty_available)

        qty_available = pos.qty_available
    except ValueError:
        # Handle the case where the string does not represent a number
        print(f"Error: is not a valid number.")
        return None

    return qty_available


def opps(data, api):
    """
    Trailing orders and other types need to take an opposite side to fill the order.
    Check the current position side and take the opposite side.
    """
    action = data.get("action")
    pos = get_position(data, api)

    if data.get("pos") is not False:
        side = (
            pos.side.lower()
            # @TODO: errors out with no side....
        )  # make position.side lowercase for comparison with action returns long or short

        if side in ["long", "buy"]:
            action = "sell"
        elif side in ["short", "sell"]:
            action = "buy"
        else:
            action = "buy"

    return action


def sp(data, api):
    """
    The logic here is to determine if the signal should be traded or not.
    If we have a posistion then we need to analyze it to determine if we buy more or exit the trade
    If there is no position and the side is the same as the action then trade that we prefer to trade on
    if
    """
    side = data.get("side")
    action = data.get("action")
    ticker = data.get("ticker")

    # if  data.get("qty") == 0 or data.get("notional") == 0:
    #    print(f"Skipping {ticker} because qty is 0")
    #    return False

    if data.get("pos") is not False:
        # If position need to analyze it and make sure it's on the same side
        print(f"SMASH OR PASS for {ticker} POS is NOT false let's do analyze")
        return anal(data, api)
    elif data.get("pos") is False and side == action:
        # No position side == action which means same intention from signal to strategy
        print(
            f"SMASH OR PASS POS of {ticker} IS {False} and my side: {side} == action: {action}"
        )
        return True
    elif side == action:
        # No position and there's no side then set the g.data["sp"] to True to trade all the things
        print(f"SMASH OR PASS side: {side} action: {action} ")
        return True
    else:
        print(
            f"SMASH OR PASS ALL HAS FAILED for ticker: {ticker}, side: {side} action: {action}"
        )
        return False


def anal(data, api):
    """
    Gives the hook an opportunity to justify the order or not.
    Already in a position and there's no profit.
    Stay in position but trade more at same side and don't switch.

    If there's no profit and the action isn't the same then skip for same side trades.
    """

    action = data.get("action")
    pos = data.get("pos")
    profit = data.get("profit")

    # make position.side lowercase for comparison with action returns long or short
    side = pos.side.lower()

    # match naming convention of action
    if side in ["long", "buy"]:
        side = "buy"
    else:
        side = "sell"

    if profit <= 0 and side == action:
        # if no profit and side is action which matches strategy then need to trade more
        print(
            f"Buy {pos.symbol} with action {action} in favor or same side {side} P/L {profit}"
        )
        return True
    elif profit <= 0 and side != action:
        # if no profit and the action is not the same to side then skip
        print(
            f"Skipping {pos.symbol} with action {action} in favor or same side {side} P/L {profit}"
        )
        return False
    elif profit >= 0 and side != action:
        # if position and there's profit and the action is not the same to side then close and continue
        print(
            f"Closing position {pos.symbol} with action {action} on {side} side P/L {profit}"
        )
        print(f"Closing position {pos.symbol}")
        api.close_position(pos.symbol)
        print(f"Closed all position(s) for {pos.symbol}")
        return True
    else:
        # all else return true
        print(f"There is no position and no profit and side does not equal action")
        return True
