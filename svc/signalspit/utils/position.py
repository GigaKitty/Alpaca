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


def anal(api, data, pos):
    """
    Gives the hook an opportunity to justify the order or not.
    Basically if we're already in a position and there's no profit.
    Then stay in position but buy more at same side and don't switch.

    If there's no profit and the action isn't the same then we skip for same side trades.
    """
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
        print(pos.unrealized_pl)
        print(f"Buy {pos.symbol} @ {side} side")
        return True
    # if we're in a position and there's no profit and the action is not the same to side then we skip
    elif profit <= 0 and side != action:
        print(pos.unrealized_pl)
        print("Skip for same side trades")
        return False
    # if we're in a position and there's profit and the action is not the same to side then we close and continue
    elif profit >= data.get("threshold") and side != action:
        print(f"Closing position {pos.symbol}")
        api.close_position(pos.symbol)
        print(f"Closed position {pos.symbol}")
        return True
    # all else return true
    else:
        print("Continue")
        return True


def close_profitable():
    """
    Checks all profitable open positions and closes them
    """
    positions = api.list_positions()
    for position in positions:
        if position.unrealized_pl > 10:
            print(f"Closing {position.symbol} for {position.unrealized_pl}")
            api.close_position(position.symbol)
            print(f"Closed {position.symbol} for {position.unrealized_pl}")
    return True
