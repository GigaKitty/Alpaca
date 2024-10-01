from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils.performance import timeit_ns

equity_aristocrats = Blueprint("equity_aristocrats", __name__)


@equity_aristocrats.route("/aristocrats", methods=["POST"])
@timeit_ns
def order():
    """
    - Places a simple market order of BUY based on TradingView WebHook
    - If the action is not BUY, skip the webhook
    - If the action is BUY, place a market order with the specified notional value
    - Return a success message if the order is placed successfully
    - Return an error message if the order placement fails
    """
    if g.data.get("action") == "buy":
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
            response_data = {"message": "🟢🎩Aristocrats - order processed"}
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error("🔴🎩Aristocrats - Error processing request: %s", str(e))
            error_message = {"error": "🔴🎩Aristocrats - Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "🟡🎩Aristocrats - Skip webhook"}
        return jsonify(skip_message), 204
