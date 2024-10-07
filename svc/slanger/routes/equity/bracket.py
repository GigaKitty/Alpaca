from flask import Blueprint, jsonify, g
from alpaca.trading.requests import (
    MarketOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
    OrderClass,
)
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import calc, order as order_utils, position
from utils.performance import timeit_ns


equity_bracket = Blueprint("equity_bracket", __name__)


@equity_bracket.route("/bracket", methods=["POST"])
@timeit_ns
def bracket():
    """
    - When there's an Open position and the side of the position is not the same as the action, close the position
    - Calculate the stop price, stop limit price, and profit limit price based on the action
    - Place a bracket order with the calculated prices
    """
    # if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
    #     try:
    #         # Close all open orders and position for the symbol
    #         open_orders = order_utils.get_orders_for_ticker(g.data.get("ticker"))

    #         # Cancel all open orders by ID
    #         for order in open_orders:
    #             api.cancel_order_by_id(order["id"])
    #             app.logger.debug(f"Cancelled order {order['id']}")

    #         # Close the position
    #         api.close_position(g.data.get("ticker"))
    #         # Wait for the position to close
    #         position.wait_position_close(g.data, api)
    #     except Exception as e:
    #         app.logger.error(
    #             f"🔴 Failed to close position for {g.data.get('ticker')}: {e}"
    #         )
    #         error_message = {
    #             "error": f"🔴 Failed to close position for {g.data.get('ticker')}: {e}"
    #         }
    #         return jsonify(error_message), 400

    #     while True:
    #         try:
    #             # get the position for the symbol
    #             pos = api.get_position(g.data.get("ticker"))
    #             if pos.qty == "0":
    #                 break
    #         except Exception:
    #             break

    try:
        calc_profit_limit_price = calc.profit_limit_price(g.data)
        calc_stop_limit_price = calc.stop_limit_price(g.data)
        calc_stop_price = calc.stop_price(g.data)

        app.logger.debug(
            "🦕 BRACKET %s on %s", g.data.get("action"), g.data.get("ticker")
        )
        app.logger.debug("price: %s", g.data.get("price"))
        app.logger.debug("calc_profit_limit_price: %s", calc_profit_limit_price)
        app.logger.debug("calc_stop_price: %s", calc_stop_price)
        app.logger.debug("calc_stop_limit_price: %s", calc_stop_limit_price)

        order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            after_hours=g.data.get("after_hours"),
            take_profit=TakeProfitRequest(limit_price=calc_profit_limit_price),
            stop_loss=StopLossRequest(
                stop_price=calc_stop_price,
                limit_price=calc_stop_limit_price,
            ),
            client_order_id=g.data.get("order_id"),
        )

        app.logger.debug("🧾 Order Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("🧾 Order: %s", order)
        response_data = {"message": "🟢🦕Bracket order submitted"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("🔴 Error processing request for bracket 🦕 order: %s", str(e))
        error_message = {"error": "🔴 Failed to process webhook request for bracket 🦕"}
        return jsonify(error_message), 400
