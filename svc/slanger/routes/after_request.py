from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import TrailingStopOrderRequest
from config import api, app, POSTPROCESS
from flask import Flask, g, jsonify, make_response
from time import sleep
import time
from utils.performance import timeit_ns
import math
import threading


def trailing_stop(data, response):
    if response.status_code == 200:
        app.logger.debug("🤠 Trailing Order")
        #app.logger.debug(f"Data: {g.data}")
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

def trailing_stop_tiered(data, response):
    if response.status_code == 200:
        app.logger.debug("🤠 Trailing Order")
        # Prepare the data for the POST request
        trailing_data = {
            "ticker": data.get("ticker"),
            "qty": data.get("qty_available"),
            "action": data.get("action"),
            "trail_percent": data.get("trail_percent"),
            "order_id": data.get("order_id"),
            # Add any other necessary fields
        }
        
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
            qty_available = float(g.data.get("qty_available"))
            if qty_available >= 5:
                chunk_size = math.floor(qty_available / 5)
                trailing_percents = [0.1, 0.2, 0.3, 0.4, 0.5]
                for i in range(5):
                    trailing_stop_data = TrailingStopOrderRequest(
                        symbol=g.data.get("ticker"),
                        qty=chunk_size,
                        side=g.data.get("opps"),
                        time_in_force=TimeInForce.GTC,
                        after_hours=g.data.get("after_hours"),
                        trail_percent=trailing_percents[i],
                        client_order_id=g.data.get("order_id") + f"trailing_{i}",
                    )
                    app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

                    trailing_stop_order = api.submit_order(order_data=trailing_stop_data)
                    app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)
            else:
                app.logger.error("Quantity available is less than 5, cannot split into chunks.")
                error_message = {"error": "Quantity available is less than 5, cannot split into chunks."}
                return make_response(jsonify(error_message), 400)

            response_data = {"message": "Webhook received and processed successfully"}
            return make_response(jsonify(response_data), 200)
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return make_response(jsonify(error_message), 400)

    app.logger.debug(f"response: {response}")

def update_price(data, response):
    # while the order id exists
    while True:
        try:
            print(f"Data: {data}")
            # Fetch the current price and update the order
            # update_order_price(order_id, current_price)
            # app.logger.info(f"Updated price for order {order_id} to {current_price}")
        except Exception as e:
            app.logger.error(f"Error updating price for order {order_id}: {e}")

        time.sleep(60)  # Wait for 1 minute before updating again


def half_supertrend(data, response):
    # Set the interval for the update
    thread = threading.Thread(
        target=update_price,
        args=(
            data,
            response,
        ),
    )
    thread.daemon = True  # Ensure the thread exits when the main program exits
    thread.start()


@app.after_request
@timeit_ns
def after_request(response):
    if hasattr(g, 'data'):
        postprocess_list = g.data.get("postprocess")
        print(f"Postprocess list: {postprocess_list}")
        if isinstance(postprocess_list, list) and any(
            item in POSTPROCESS for item in postprocess_list
        ):
            for func in postprocess_list:
                if func == "half_supertrend":
                    half_supertrend(g.data, response)
                elif func == "trailing_stop":
                    trailing_stop(g.data, response)
                elif func == "trailing_stop_tiered":
                    trailing_stop_tiered(g.data, response)
    
    return response  # @IMPORTANT: Do not remove this line
