import math
import string


############################################################
# Gets currently open position for ticker
def get(data, api):
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


def qty_available(data, api):

    qty_available = data.get("qty")

    try:
        position = get(data, api)
        qty_available = float(position.qty_available)
        print("======================================================")
        print(position, qty_available)
        print("======================================================")
    except ValueError:
        # Handle the case where the string does not represent a number
        print(f"Error: is not a valid number.")
        return None

    return abs(qty_available)


def opps(data):
    """
    Trailing orders and other types need to take an opposite side to fill the order.
    Check the current position side and take the opposite side.
    """
    action = data.get("action")
    pos = data.get("pos")
    side = (
        pos.side.lower()
    )  # make position.side lowercase for comparison with action returns long or short

    if side == "long":
        action = "sell"
    elif side == "short":
        action = "buy"

    return action


def sp(data, api):
    if data.get("pos") is not False:
        # If position need to analyze it and make sure it's on the same side
        return anal(data, api)
    elif data.get("pos") is False and data.get("side") == data.get("action"):
        # No position side == action which means same intention from signal to strategy
        return True
    else:
        # No position and there's no side then set the g.data["sp"] to True to trade all the things
        return True


def anal(data, api):
    """
    Gives the hook an opportunity to justify the order or not.
    Already in a position and there's no profit.
    Stay in position but trade more at same side and don't switch.

    If there's no profit and the action isn't the same then skip for same side trades.
    """

    action = data.get("action")
    pos = data.get("pos")
    profit = float(pos.unrealized_pl)

    # make position.side lowercase for comparison with action returns long or short
    side = pos.side.lower()

    # match naming convention of action
    if side == "long":
        side = "buy"
    else:
        side = "sell"

    if profit <= 0 and side == action:
        # if no profit and side is action which matches strategy then need to trade more
        print(f"Buy {pos.symbol} @ {side} side P/L {pos.unrealized_pl}")
        return True
    elif profit <= 0 and side != action:
        # if no profit and the action is not the same to side then skip
        print(
            f"Skip {pos.symbol} @ {side} for same side trades P/L {pos.unrealized_pl}"
        )
        return False
    elif profit >= data.get("profit") and side != action:
        # if position and there's profit and the action is not the same to side then close and continue
        print(f"Closing position {pos.symbol}")
        api.close_position(pos.symbol)
        print(f"Closed position {pos.symbol}")
        return True
    # all else return true
    else:
        print("Continue")
        return True
