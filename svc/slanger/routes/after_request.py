from config import api, app, POSTPROCESS
import math
from time import sleep
from alpaca.trading.requests import TrailingStopOrderRequest
from alpaca.trading.enums import TimeInForce
from utils.performance import timeit_ns
from flask import Flask, g, jsonify, make_response


def trailing_stop(data):
    if response.status_code == 200 and data.get("trailing") is True:
        app.logger.debug("Trailing stop order passed 🤠🤠🤠🤠🤠🤠🤠🤠")
        app.logger.debug(f"qty_available: {g.data.get('qty_available')}")
        # app.logger.debug(f"Data: {g.data}")
        # send an order request to the trailing endpoint
        # Prepare the data for the POST request
        trailing_data = {
            "ticker": data.get("ticker"),
            "qty": data.get("qty_available"),
            "action": data.get("action"),
            "trail_percent": data.get("trail_percent"),
            "order_id": data.get("order_id"),
            # Add any other necessary fields
        }
        app.logger.debug(f"Trailing stop data: {trailing_data}")

        max_attempts = 10
        for attempt in range(max_attempts):
            if attempt > max_attempts:
                print("💪💪💪💪💪💪were maxed out")
                return False

            ord = api.get_order_by_client_id(g.data.get("order_id"))
            app.logger.debug(f"Order status: {ord.status}")

            # Define the possible values for ord.status
            invalid = {"canceled", "expired", "replaced", "pending_cancel"}
            valid = {"filled", "partially_filled"}

            app.logger.debug(f"Order status: {ord}")
            if ord.status in invalid:
                print(f"order status: {ord.status}")
                app.logger.debug(f"Order status: is {ord.status} so we're breaking")
                break
            elif ord.status in valid:
                print(f"order status: {ord.status}")
                app.logger.debug(
                    f"Order status: is {ord.status} so we're continuing to place order"
                )
            else:
                sleep(5)
                continue

        try:
            qty_available_rounded = math.floor(float(g.data.get("qty_available")))
            trailing_stop_data = TrailingStopOrderRequest(
                symbol=g.data.get("ticker"),
                qty=qty_available_rounded,
                side=g.data.get("opps"),
                time_in_force=TimeInForce.GTC,
                after_hours=g.data.get("after_hours"),
                trail_percent=g.data.get("trail_percent"),
                client_order_id=g.data.get("order_id") + "trailing",
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


def half_supertrend(data, response):
    # get current quantity of the position
    if g.data.get("pos") is not False:
        app.logger.debug(f"Spawning half supertrend order")
        # Get the total available quantity and split it into quarters based on fibbonaccie sequence
        app.logger.debug(f"qty_available: {g.data.get('qty_available')}")
        app.logger.debug(f"response: {response}")
    

@app.after_request
@timeit_ns
def after_request(response):
    postprocess_list = g.data.get("postprocess")
    if isinstance(postprocess_list, list) and any(
        item in POSTPROCESS for item in postprocess_list
    ):
        for func in postprocess_list:
            if func == "half_supertrend":
                half_supertrend(g.data, response)

    return response  # @IMPORTANT: Do not remove this line
