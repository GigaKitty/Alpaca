from flask import Blueprint, jsonify, g
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils.performance import timeit_ns

equity_limit = Blueprint("equity_limit", __name__)


@equity_limit.route("/limit", methods=["POST"])
@timeit_ns
def limit():
    try:
        order_data = LimitOrderRequest(
            symbol=g.data.get("ticker"),
            notional=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.DAY,
            limit_price=g.data.get("limit_price"),
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("Limit Order Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("Limit Order: %s", order)
        response_data = {"message": "Limit order processed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing limit order request: %s", str(e))
        error_message = {"error": "Limit order processing failed"}
        return jsonify(error_message), 400
