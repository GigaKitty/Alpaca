from flask import Blueprint, jsonify, g, request
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import position
from utils.performance import timeit_ns
from utils import calc, order as order_utils, position

equity_supertrend = Blueprint("equity_supertrend", __name__)

memory = {}

@equity_supertrend.route("/supertrend", methods=["POST"])
@timeit_ns
def order():
    """
    - This supertrend is based off of the supertrend indicator and a breakout strategy.
    - It expects three webhooks to be sent to the endpoint:
        - one for breaking down, one for breaking up, and one for the supertrend
    
    """

    if g.data.get("comment")  in ["downward_breakout", "upward_breakout"]:
        memory[g.data.get("ticker")] = {
            "action": request.json.get("action"),
            "comment": g.data.get("comment")
        }
    
        return jsonify({"message": "breakout saved to memory"}), 200
    

    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"): 
        try:
           # # Close all open orders and position for the symbol
            open_orders = order_utils.get_orders_for_ticker(g.data.get("ticker"))

            # Cancel all open orders by ID
            for order in open_orders:
                api.cancel_order_by_id(order["id"])
                app.logger.debug(f"Cancelled order {order['id']}")

            # Close the position
            api.close_position(g.data.get("ticker"))
            # Wait for the position to close
            position.wait_position_close(g.data, api)

        except Exception as e:
            app.logger.error(f"🔴 Failed to close position for {g.data.get('ticker')}: {e}")
            error_message = {
                "error": f"🔴 Failed to close position for {g.data.get('ticker')}: {e}"
            }
            return jsonify(error_message), 400

    try:
        # Place the initial market order
        order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.IOC,
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("SuperTrend Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("SuperTrend Order: %s", order)

        response_data = {"message": "Webhook received and processed successfully"}
        return jsonify(response_data), 200

    except Exception as e:
        app.logger.error("Error processing request: %s", str(e))
        error_message = {"error": "Failed to process webhook request"}
        return jsonify(error_message), 400
    
    finally:
        print("Finally block")
        # confirm the trade and if not we retry to ensure the trade is executed and is on the right side