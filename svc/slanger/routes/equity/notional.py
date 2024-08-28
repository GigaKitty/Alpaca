from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app

equity_notional = Blueprint('equity_notional', __name__)

# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
# @NOTE: some stocks and ETFs are not allowed to sell short in notional i.e. BKKT, EDIT,
@equity_notional.route("/notional", methods=["POST"])
def order():
    """
    purchase a dollar amount of a stock or ETF based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    # Check if we should process the request
    if g.data.get("sp") is True:
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
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204

