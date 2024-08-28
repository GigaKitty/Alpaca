from flask import Blueprint, jsonify, g
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app

crypto_limit = Blueprint('crypto_limit', __name__)

@crypto_limit.route("/limit", methods=["POST"])
def order():
    """
    Places a limit order based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """   
    if g.data.get("sp") is True:
        try:
            order_data = LimitOrderRequest(
                symbol=g.data.get("ticker"),
                notional=g.data.get("notional"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.GTC,
                after_hours=g.data.get("after_hours"),
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