from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app, POSTPROCESS
from utils.performance import timeit_ns

crypto_market = Blueprint("crypto_market", __name__)


@crypto_market.route("/market", methods=["POST"])
@timeit_ns
def order():
    try:
        order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=1, #@TODO: Change this to g.data.get("qty") after fixing
            side=g.data.get("action"),
            time_in_force=TimeInForce.IOC,
            client_order_id=g.data.get("order_id"),
        )
        order = api.submit_order(order_data=order_data)
        app.logger.debug(
            "🪙  Crypto Market Order placed for %s on ticker %s ",
            order.qty,
            g.data.get("ticker"),
        )
        
        order_dict = order.__dict__

        response_data = {"order": order_dict}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing 🪙 Crypto Market Order request: %s", str(e))
        error_message = {"error": "Failed to process🪙 Crypto Market request"}
        return jsonify(error_message), 400
