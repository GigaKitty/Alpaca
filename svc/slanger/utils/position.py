from flask import request, jsonify
from config import api, app
import time


############################################################
# Gets currently open position for ticker
def get_position(data, api) -> bool:
    """
    Checks the position of the current ticker
    """
    try:
        position = api.get_open_position(data.get("ticker"))
        app.logger.debug("Position: %s", position)
        if position is None:
            return False
        else:
            return position
    except Exception as e:
        return False


def wait_position_close(data, api, timeout=60):
    """
    Wait until the position is closed.

    :param data: The data containing the ticker information.
    :param api: The API instance to interact with the trading platform.
    :param timeout: The maximum time (in seconds) to wait for the position to close.
    """
    ticker = data.get("ticker")
    start_time = time.time()

    # Wait until the position is closed for the specified timeout duration in seconds
    while time.time() - start_time < timeout:
        try:
            position = get_position(data, api)
            app.logger.debug(f"Position: {position}")
            if position is not None and position.qty == 0:
                app.logger.info(f"Position for {ticker} is closed.")
                return True
        except Exception as e:
            app.logger.error(f"Error checking position status for {ticker}: {e}")
            return False

        app.logger.info(f"Position for {ticker} is still open. Checking again ...")

    app.logger.error(
        f"Timeout: Position for {ticker} did not close within {timeout} seconds."
    )

    return False


def get_current_price(data, api):
    pos = get_position(data, api)
    if pos is not False:
        return float(pos.current_price)


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


# @TODO: deprecated
# def sp(data, api):
#     """
#     The logic here is to determine if the signal should be traded or not.
#     If we have a position then we need to analyze it to determine if we buy more or exit the trade
#     If there is no position and the side is the same as the action then trade that we prefer to trade on
#     if
#     """
#     side = data.get("side")
#     action = data.get("action")
#     ticker = data.get("ticker")

#     if data.get("pos") is not False:
#         app.logger.debug("Position: %s", data.get("pos"))
#         return anal(data, api)
#     elif data.get("pos") is False and side == action:
#         app.logger.debug(f"No position on {ticker} and side/{side} == action/{action} return True")
#         return True
#     else:
#         app.logger.debug(f"SP ALL HAS FAILED for ticker: {ticker}, side: {side} action: {action} return False")
#         return False


# def anal(data, api):
#     """
#     Gives the hook an opportunity to justify the order or not.
#     Already in a position and there's no profit.
#     Stay in position but trade more at same side and don't switch.

#     If there's no profit and the action isn't the same then skip for same side trades.
#     """
#     action = data.get("action")
#     pos = data.get("pos")
#     profit = data.get("profit")
#     neversell = data.get("neversell", False)

#     # check request endpoint if it's a crypto order
#     if request.endpoint.startswith("crypto"):
#         profit_margin = float(pos.market_value) * data.get("profit_margin", 0.03)
#     else:
#         profit_margin = float(pos.market_value) * data.get("profit_margin", 0.0001)

#     # make position.side lowercase for comparison with action returns long or short
#     side = pos.side.lower()

#     app.logger.debug(f"Position: {pos.symbol} Profit: {profit} Profit Margin: {profit_margin} Side: {side} Action: {action}")
#     app.logger.debug(request.endpoint)
#     # match naming convention of action
#     if side in ["long", "buy"]:
#         side = "buy"
#     else:
#         side = "sell"

#     if profit <= profit_margin and side == action:
#         app.logger.debug(f"{action} {pos.symbol} with action {action} in favor or same side {side} P/L {profit} return True")
#         return True
#     elif profit <= profit_margin and side != action:
#         app.logger.debug(f"Skipping {pos.symbol} with action {action} in favor or same side {side} P/L {profit} return False")
#         return False
#     elif profit >= profit_margin and side != action and not request.endpoint.startswith("equity_bracket") and neversell is False:
#         app.logger.debug(f"Closing position {pos.symbol} with action {action} on {side} side P/L {profit} return True")
#         api.close_position(pos.symbol)
#         app.logger.debug(f"Closed all position(s) for {pos.symbol}")
#         return False
#     else:
#         app.logger.debug(f"There is no position and no profit place trade in either direction return True")
#         return True
