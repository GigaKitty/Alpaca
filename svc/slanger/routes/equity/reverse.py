
from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import position

equity_reverse = Blueprint('equity_reverse', __name__)

@equity_reverse.route("/reverse", methods=["POST"])
def order():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    app.logger.debug("Position Data: %s", g.data)
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        app.logger.debug("Closing Position: %s", g.data.get("ticker"))
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(f"Failed to close position for {g.data.get('ticker')}: {e}")
    
    if g.data.get("comment") == "Close entry(s) order Long" or g.data.get("comment") == "Close entry(s) order Short":
        return jsonify({"message": "Webhook received and processed successfully"}), 200
    
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

    skip_message = {"Skip": "Skip webhook"}
    return jsonify(skip_message), 204
