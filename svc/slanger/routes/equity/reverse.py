
from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app

equity_reverse = Blueprint('equity_reverse', __name__)

@equity_reverse.route("/reverse", methods=["POST"])
def order():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    # if there's a position and side is equal to action
    if g.data.get("pos") is not False and g.data.get("side") == g.data.get("action"):
        # buy more
        # quantity equals quantity
        quantity = g.data.get("qty")
    elif g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        # reverse position
        quantity = g.data.get("quantity_available") * 2
    else: 
        quantity = g.data.get("qty")


    if g.data.get("sp") is True:
        try:
            order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=quantity,
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

            response_code = 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204
