from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import TrailingStopOrderRequest
from config import api, app, POSTPROCESS
from flask import Flask, g, jsonify, make_response
from time import sleep
from utils.performance import timeit_ns
import math
import asyncio

def calculate_range(price):
    if price >= 200:
        return 0.25
    elif price >= 100:
        return 0.1
    else:
        return 1.0
    
async def check_order_status(order_id, max_attempts=10):
    for attempt in range(max_attempts):
        if attempt >= max_attempts:
            print("💪 We're maxed out")
            return False

        ord = api.get_order_by_client_id(order_id)
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
    return True


async def trailing_stop(data, response):
    if response.status_code == 200 and await check_order_status(g.data.get("order_id")):
        app.logger.debug("🤠 Trailing Order")
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


async def trailing_stop_tiered(data, response):
    if response.status_code == 200 and await check_order_status(g.data.get("order_id")):
        app.logger.debug("🤠 Trailing Order")
        try:
            # @NOTE: this is going to bug out but I'm going to leave it for now until I can test it
            base = float(g.data.get("base"))
            qty_available = (
                float(g.data.get("qty_available")) - base
            )  # We remove base so we have a reserve to let run

            if qty_available and base > 1:
                calculated_range = calculate_range(float(g.data.get("close")))
                trailing_percents = [
                    round(0.1 + i * (calculated_range - 0.1) / (base - 1), 2) for i in range(base)
                ]  # This will create a list of trailing percents from 0.1 to 0.25, rounded to two decimals
                for i in range(1, int(qty_available / base) + 1):
                    trailing_stop_data = TrailingStopOrderRequest(
                        symbol=g.data.get("ticker"),
                        qty=i,
                        side=g.data.get("opps"),
                        time_in_force=TimeInForce.GTC,
                        after_hours=g.data.get("after_hours"),
                        trail_percent=round(trailing_percents[i]),
                        client_order_id=g.data.get("order_id") + f"trailing_{i}",
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


@app.after_request
@timeit_ns
def after_request(response):
    if hasattr(g, "data"):
        postprocess_list = g.data.get("postprocess")
        print(f"Postprocess list: {postprocess_list}")
        if isinstance(postprocess_list, list) and any(
            item in POSTPROCESS for item in postprocess_list
        ):
            for func in postprocess_list:
                if func == "trailing_stop":
                    asyncio.run(trailing_stop(g.data, response))
                elif func == "trailing_stop_tiered":
                    asyncio.run(trailing_stop_tiered(g.data, response))

    return response  # @IMPORTANT: Do not remove this line
