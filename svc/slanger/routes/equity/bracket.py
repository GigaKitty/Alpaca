from flask import Blueprint, jsonify, g
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest, OrderClass
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils import calc

equity_bracket = Blueprint('equity_bracket', __name__)


@equity_bracket.route("/bracket", methods=["POST"])
def order():
    """
    Places a bracket order based on WebHook data
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("sp") is True:
        try:
            calc_stop_limit_price = round(calc.stop_limit_price(g.data), 2)
            calc_profit_limit_price = round(calc.profit_limit_price(g.data), 2)
            calc_stop_price = round(calc.stop_price(g.data), 2)

            order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.BRACKET,
                after_hours=g.data.get("after_hours"),
                take_profit=TakeProfitRequest(limit_price=calc_profit_limit_price),
                stop_loss=StopLossRequest(
                    stop_price=calc_stop_price,
                    limit_price=calc_stop_limit_price,
                ),
                client_order_id=g.data.get("order_id"),
            )
            app.logger.debug("Order Data: %s", order_data)
            order = api.submit_order(order_data=order_data)
            app.logger.debug("Order: %s", order)
            response_data = {"message": "Webhook received and processed successfully"}
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204

