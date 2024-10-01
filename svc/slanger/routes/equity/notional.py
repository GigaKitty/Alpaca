from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import position

equity_notional = Blueprint('equity_notional', __name__)

# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
# @NOTE: some stocks and ETFs are not allowed to sell short in notional i.e. BKKT, EDIT,
@equity_notional.route("/notional", methods=["POST"])
def order():
    """
    purchase a dollar amount of a stock or ETF based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("pos") is not False and g.data.get("side") != g.data.get("action"):
        try:
            api.close_position(g.data.get("ticker"))
            position.wait_position_close(g.data, api)
        except Exception as e:
            app.logger.error(
                f"Failed to close position for {g.data.get('ticker')}: {e}"
            )
            error_message = {"error": f"Failed to close position for {g.data.get('ticker')}: {e}"}
            return jsonify(error_message), 400
    app.logger.debug("data: %s", g.data)
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