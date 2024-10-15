from flask import Blueprint, jsonify, g, make_response
from alpaca.trading.requests import TrailingStopOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils.performance import timeit_ns
from utils import order as order_utils

equity_trailing_stop = Blueprint("equity_trailing_stop", __name__)


@equity_trailing_stop.route("/trailing_stop", methods=["POST"])
@timeit_ns
async def trailing_stop(data, response):

    if response.status_code == 200 and await order_utils.check_order_status(
        data.get("order_id")
    ):
        try:
            trailing_stop_data = TrailingStopOrderRequest(
                symbol=data.get("ticker"),
                qty=data.get("qty"),
                side=data.get("opps"),
                time_in_force=TimeInForce.GTC,
                after_hours=data.get("after_hours"),
                trail_percent=data.get("trail_percent"),
                client_order_id=data.get("order_id") + "_trailing",
            )
            app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

            trailing_stop_order = api.submit_order(order_data=trailing_stop_data)
            app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)

            response_data = {"message": "Webhook received and processed successfully"}
            return make_response(jsonify(response_data), 200)
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return make_response(jsonify(error_message), 400)

    app.logger.debug(f"response: {response}")
