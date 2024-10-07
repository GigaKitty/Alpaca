from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils.performance import timeit_ns

equity_market = Blueprint("equity_market", __name__)


@equity_market.route("/market", methods=["POST"])
@timeit_ns
def market():
    try:
        order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.IOC,
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("Market Order Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("Market Order: %s", order)
        response_data = {"message": "Market order processed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing Market order request: %s", str(e))
        error_message = {"error": "Market order processing failed"}
        return jsonify(error_message), 400
