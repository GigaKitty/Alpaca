from flask import Blueprint, jsonify, g
from alpaca.trading.requests import StopLimitOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app

crypto_stop_limit = Blueprint('crypto_stop_limit', __name__)

@crypto_stop_limit.route("/stop_limit", methods=["POST"])
def order():
    if g.data.get("sp") is True:
        try:
            order_data = StopLimitOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.IOC,
                after_hours=g.data.get("after_hours"),
                stop_price=g.data.get("stop_price"),
                limit_price=g.data.get("limit_price"),
                client_order_id=g.data.get("order_id"),
            )
            app.logger.debug("Data: %s", order_data)
            order = api.submit_order(order_data=order_data)
            app.logger.debug("Order: %s", order)
            response_data = {"message": "Webhook received and processed successfully"}
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204   