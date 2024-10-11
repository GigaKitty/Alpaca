from flask import Blueprint, jsonify, g, make_response
from alpaca.trading.requests import TrailingStopOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
from utils.performance import timeit_ns
from utils import order as order_utils

equity_trailing_stop_tiered = Blueprint("equity_trailing_stop_tiered", __name__)


@equity_trailing_stop_tiered.route("/trailing_stop_tiered", methods=["POST"])
async def trailing_stop_tiered(data, response):
    app.logger.debug(data.get("ticker"))
    app.logger.debug(response.status_code)
    if response.status_code == 200 and await order_utils.check_order_status(
        data.get("order_id")
    ):
        ticker = data.get("ticker")
        app.logger.debug(f"🤠 Trailing Stop Tiered {ticker}")
        app.logger.debug(data.get("order_id"))
        # response_data = {"message": "Webhook received and processed successfully"}
        # return make_response(jsonify(response_data), 200)
        try:
            # @NOTE: this is going to bug out but I'm going to leave it for now until I can test it
            base = float(data.get("base"))
            qty_available = (
                float(data.get("qty_available")) - base
            )  # We remove base so we have a reserve to let run


            if qty_available and base > 1:
                calculated_range = calculate_range(float(data.get("close")))
                trailing_percents = [
                    round(0.1 + i * (float(data.get("trail_percent")) - 0.1) / (base - 1), 2)
                    for i in range(base)
                ]  # This will create a list of trailing percents from 0.1 to 0.25, rounded to two decimals
                for i in range(1, int(qty_available / base) + 1):
                    trailing_stop_data = TrailingStopOrderRequest(
                        symbol=data.get("ticker"),
                        qty=float(i),
                        side=data.get("opps"),
                        time_in_force=TimeInForce.GTC,
                        after_hours=data.get("after_hours"),
                        trail_percent=round(trailing_percents[i]),
                        client_order_id=data.get("order_id") + f"trailing_{i}",
                    )
                    app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

                    trailing_stop_order = api.submit_order(
                        order_data=trailing_stop_data
                    )
                    app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)
            else:
                app.logger.error(
                    "Quantity available is less than 5, cannot split into chunks."
                )
                error_message = {
                    "error": "Quantity available is less than 5, cannot split into chunks."
                }
                return make_response(jsonify(error_message), 400)

            response_data = {"message": "Webhook received and processed successfully"}
            return make_response(jsonify(response_data), 200)
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return make_response(jsonify(error_message), 400)

    app.logger.debug(f"response: {response}")
