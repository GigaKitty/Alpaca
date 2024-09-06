
from flask import Blueprint, jsonify, g
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import position
import time
import threading

equity_reverselimit = Blueprint('equity_reverselimit', __name__)

@equity_reverselimit.route("/reverselimit", methods=["POST"])
def order():
    """
    Places a simple order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        app.logger.debug("Closing Position: %s", g.data.get("ticker"))
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(f"Failed to close position for {g.data.get('ticker')}: {e}")
    
    # Only applies to the SMA strategy because it has close entry(s) order Long and Short
    if g.data.get("comment") == "Close entry(s) order Long" or g.data.get("comment") == "Close entry(s) order Short":
        return jsonify({"message": "Webhook received and processed successfully"}), 200

    # Take the high and the low to find the spread divide by 4 into quadrants get the limit price
    calc_spread = round(float(g.data.get("high")) - float(g.data.get("low")), 2) / 4

    # Calculate prices based on a candle spread broken into 4 quadrants
    if g.data.get("action") == "buy":
        calc_limit_price = round(float(g.data.get("low")), 2) + calc_spread
    elif g.data.get("action") == "sell":
        calc_limit_price = round(float(g.data.get("high")), 2) - calc_spread
    
    app.logger.debug("Spread: %s", calc_spread)
    app.logger.debug("Limit Price: %s", calc_limit_price)
   
    try:
        order_data = LimitOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.DAY,
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
            limit_price=round(calc_limit_price, 2),
        )

        app.logger.debug("Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("Order: %s", order)
        
        # Schedule a task to cancel the order after 1 minute
        def cancel_order_after_1_minute(api, order_id):
            time.sleep(60)  # Wait for 1 minute
            try:
                api.cancel_order_by_id(order_id)
                app.logger.debug(f"Order {order_id} canceled after 1 minute")
            except Exception as e:
                app.logger.error(f"Failed to cancel order {order_id}: {e}")

        threading.Thread(target=cancel_order_after_1_minute, args=(api, order.id,)).start()

        response_data = {"message": "Webhook received and processed successfully"}
        return jsonify(response_data), 200

    except Exception as e:
        app.logger.error("Error processing request: %s", str(e))
        error_message = {"error": "Failed to process webhook request"}
        return jsonify(error_message), 400