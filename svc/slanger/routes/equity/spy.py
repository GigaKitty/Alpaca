
from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, TakeProfitRequest
from alpaca.trading.enums import TimeInForce
from config import api, app, COMMENTS
from utils import position
from utils.performance import timeit_ns

equity_spy = Blueprint('equity_spy', __name__)

@equity_spy.route("/spy", methods=["POST"])
@timeit_ns
def order():
    """
    - If there's open orders on this ticker then close them
    - When there's an Open position and the side of the position is not the same as the action, close the position
    - Place an initial market order with multiple stop loss and take profit orders
        - place 25% of the qty with a stop loss order at half of the atr level
        
                    """
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(
                f"Failed to close position for {g.data.get('ticker')}: {e}"
            )
            error_message = {"error": f"🔴 Failed to close position for {g.data.get('ticker')}: {e}"}
            return jsonify(error_message), 400
    
    try:
        # Place the initial market order
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
    
