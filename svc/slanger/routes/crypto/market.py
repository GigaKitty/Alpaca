from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app, COMMENTS
from utils import position

crypto_market = Blueprint("crypto_market", __name__)


@crypto_market.route("/market", methods=["POST"])
def order():
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(
                f"Failed to close position for {g.data.get('ticker')}: {e}"
            )
            error_message = {
                "error": f"🔴 Failed to close position for {g.data.get('ticker')}: {e}"
            }
            return jsonify(error_message), 400
        
    if g.data.get("commment") in COMMENTS:
        return jsonify({"message": "The comments was a closing tp/sl comment"}), 200

    try:
        order_data = MarketOrderRequest(
            symbol=g.data.get("ticker"),
            qty=g.data.get("qty"),
            side=g.data.get("action"),
            time_in_force=TimeInForce.IOC,
            after_hours=g.data.get("after_hours"),
            client_order_id=g.data.get("order_id"),
        )
        app.logger.debug("Market Data: %s", order_data)
        order = api.submit_order(order_data=order_data)
        app.logger.debug("Market Order: %s", order)
        response_data = {"message": "Webhook received and processed successfully"}
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error("Error processing request: %s", str(e))
        error_message = {"error": "Failed to process webhook request"}
        return jsonify(error_message), 400
