from flask import Blueprint, jsonify, g
from alpaca.trading.requests import (
    LimitOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
    OrderClass,
)
from alpaca.trading.enums import TimeInForce
from config import api, app, COMMENTS
from utils import calc, order as order_utils, position
from utils.performance import timeit_ns

equity_bracketlimit = Blueprint("equity_bracketlimit", __name__)

@equity_bracketlimit.route("/bracketlimit", methods=["POST"])
@timeit_ns
def place_order():
    """
    Places a bracketlimit order based on WebHook data
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        try:
            # Cancel all open orders for the ticker
            open_orders = order_utils.get_orders_for_ticker(g.data.get("ticker"))

            for order in open_orders:
                api.cancel_order_by_id(order["id"])
                app.logger.debug(f"Cancelled order {order['id']}")

            # Close the position
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(
                f"Failed to close position for {g.data.get('ticker')}: {e}"
            )
            error_message = {
                "error": f"Failed to close position for {g.data.get('ticker')}: {e}"
            }
            return jsonify(error_message), 400

        # Wait until the position is confirmed to be closed
        while True:
            try:
                pos = api.get_position(g.data.get("ticker"))
                if pos.qty == "0":
                    break
            except Exception:
                break  # If the position is not found, it means it's closed
            time.sleep(1)  # Wait for 1 second before checking again
        
        if g.data.get("commment") in COMMENTS:
            return jsonify({"message": "Webhook received and processed successfully"}), 200    

    try:
        # calc_profit_limit_price = round(calc.profit_limit_price(g.data), 2)
        # calc_stop_price = round(calc.stop_price(g.data), 2)
        # calc_stop_limit_price = round(calc.stop_limit_price(g.data), 2)
        # calc_limit_price = round(float(calc.limit_price(g.data)), 2)
        calc_average_price = round(
            (float(g.data.get("high")) + float(g.data.get("low"))) / 2, 2
        )
        if g.data.get("action") == "buy":
            calc_profit_limit_price = round(float(calc_average_price) + 0.09, 2)
            calc_stop_limit_price = round(float(calc_average_price) - 0.07, 2)
            calc_stop_price = round(float(calc_average_price) - 0.05, 2)
        else:
            calc_profit_limit_price = round(float(calc_average_price) - 0.09, 2)
            calc_stop_limit_price = round(float(calc_average_price) + 0.07, 2)
            calc_stop_price = round(float(calc_average_price) + 0.05, 2)

        app.logger.debug(
            "🦕 bracketlimit %s on %s", g.data.get("action"), g.data.get("ticker")
        )
        app.logger.debug("calc_profit_limit_price: %s", calc_profit_limit_price)
        app.logger.debug("calc_stop_price: %s", calc_stop_price)
        app.logger.debug("calc_stop_limit_price: %s", calc_stop_limit_price)

        order_data = LimitOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            limit_price=calc_average_price,
            after_hours=g.data.get("after_hours"),
            take_profit=TakeProfitRequest(limit_price=calc_profit_limit_price),
            stop_loss=StopLossRequest(
                stop_price=calc_stop_price,
                limit_price=calc_stop_limit_price,
            ),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("Order Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("Order: %s", order)
        response_data = {"message": "Webhook received and processed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing request: %s", str(e))
        error_message = {"error": "Failed to process webhook request"}
        return jsonify(error_message), 400
