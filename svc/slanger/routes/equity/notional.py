from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import position
from utils.performance import timeit_ns


equity_notional = Blueprint("equity_notional", __name__)


@equity_notional.route("/notional", methods=["POST"])
@timeit_ns
def notional():
    try:
        market_order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            notional=g.data.get("notional"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.DAY,
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("Market Data: %s", market_order_data)
        market_order = api.submit_order(order_data=market_order_data)
        app.logger.debug("Market Order: %s", market_order)
        response_data = {"message": "Webhook received and processed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing request: %s", str(e))
        error_message = {"error": "Failed to process webhook request"}
        return jsonify(error_message), 400