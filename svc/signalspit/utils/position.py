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
            print(f"Is this the buggy logic check?? {position}")
            return position
    except Exception as e:
        return False


def opps(data):
    """
    Trailing orders and other types need to take an opposite side to fill the order.
    Check the current position side and take the opposite side.
    """
    action = ""

    pos = data.get("pos")

    # make position.side lowercase for comparison with action returns long or short
    side = pos.side.lower()

    if side == "long":
        action = "sell"
    elif side == "short":
        action = "buy"

    return action


def sp(api, data):
    if data.get("pos") is not False:
        # If we have a position we need to analyze it and make sure it's on the side we want
        return anal(api, data)

    elif data.get("pos") is False and data.get("side") == data.get("action"):
        # If we have no position side == action which means same intention from signal to strategy
        return True
    else:
        # If we don't have a position and there's no side then we can set the g.data["sp"] to True and buy all the things
        return True


def anal(api, data):
    """
    Gives the hook an opportunity to justify the order or not.
    Basically if we're already in a position and there's no profit.
    Then stay in position but buy more at same side and don't switch.

    If there's no profit and the action isn't the same then we skip for same side trades.
    """
    pos = data.get("pos")
    profit = float(pos.unrealized_pl)
    # make position.side lowercase for comparison with action returns long or short
    side = pos.side.lower()

    # match naming convention of action
    if data.get("action") == "buy":
        action = "long"
    else:
        action = "short"

    # if we're in a position and there's no profit then we need to buy more
    if profit <= 0 and side == action:
        print(f"Buy {pos.symbol} @ {side} side P/L {pos.unrealized_pl}")
        return True
    # if we're in a position and there's no profit and the action is not the same to side then we skip
    elif profit <= 0 and side != action:
        print(
            f"Skip {pos.symbol} @ {side} for same side trades P/L {pos.unrealized_pl}"
        )
        return False
    # if we're in a position and there's profit and the action is not the same to side then we close and continue
    elif profit >= data.get("profit") and side != action:
        print(f"Closing position {pos.symbol}")
        api.close_position(pos.symbol)
        print(f"Closed position {pos.symbol}")
        return True
    # all else return true
    else:
        print("Continue")
        return True
