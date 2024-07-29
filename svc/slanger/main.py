from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderType
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
    TrailingStopOrderRequest,
)
from flask import Flask, Blueprint, g, request, jsonify, json, render_template
from utils import position, sec, order, account, calc
from prometheus_flask_exporter import PrometheusMetrics
import json
import math
import os

# import threading
# import asyncio
# import random
# import requests
# import string
import time

#######################################################
#### ENVIRONMENT SETUP ################################
#######################################################
"""
 Set the environment variable ENVIRONMENT to main or dev
"""
paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

"""
Initialize the Alpaca API
If it's dev i.e. japer trading then it uses the paper trading API
"""
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize the Flask app
app = Flask(__name__)

metrics = PrometheusMetrics(app, group_by="endpoint")

# Initialize the Blueprint for the orders
orders = Blueprint("orders", __name__)


#######################################################
#######################################################
#######################################################
@orders.route("/limit", methods=["POST"])
def limit():
    """
    Places a limit order based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("sp") is True:
        limit_price = round(calc.limit_price(g.data), 2)
        try:
            limit_order_data = LimitOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
                after_hours=g.data.get("after_hours"),
                client_order_id=g.data.get("order_id"),
            )
            app.logger.debug("Limit Order Data: %s", limit_order_data)
            limit_order = api.submit_order(order_data=limit_order_data)
            app.logger.debug("Limit Order: %s", limit_order)
            response_data = {"message": "Webhook received and processed successfully"}
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204


@orders.route("/bracket", methods=["POST"])
def bracket():
    """
    Places a bracket order based on WebHook data
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("sp") is True:
        try:
            calc_limit_price = round(calc.limit_price(g.data), 2)
            calc_profit_limit_price = round(calc.profit_limit_price(g.data), 2)
            calc_stop_price = round(calc.stop_price(g.data), 2)

            bracket_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force="gtc",
                order_class=OrderClass.BRACKET,
                after_hours=g.data.get("after_hours"),
                take_profit=TakeProfitRequest(limit_price=calc_profit_limit_price),
                stop_loss=StopLossRequest(
                    stop_price=calc_stop_price,
                    limit_price=calc_limit_price,
                ),
                client_order_id=g.data.get("order_id"),
            )
            app.logger.debug("Bracket Order Data: %s", bracket_order_data)
            bracket_order = api.submit_order(order_data=bracket_order_data)
            app.logger.debug("Bracket Order: %s", bracket_order)
            response_data = {"message": "Webhook received and processed successfully"}
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204


# @orders.route("/trailing", methods=["POST"])
def trailing():
    """
    Places a trailing stop order based on TradingView WebHook for now it only works with the trailing stop percentage that's to simplify the process and avoid losses due to complexity of the trailing stop order types i.e. trail_price, trail_percent, etc.
    @SEE: https://docs.alpaca.markets/v1.1/docs/working-with-orders#submitting-trailing-stop-orders
    """
    print(f"setting up trailing stop order")
    max_attempts = 10
    for attempt in range(max_attempts):
        if attempt > max_attempts:
            print("were maxed out")
            return False

        ord = api.get_order_by_client_id(g.data.get("order_id"))

        # Define the possible values for ord.status
        invalid = {"canceled", "expired", "replaced", "pending_cancel"}
        valid = {"filled", "partially_filled"}

        if ord.status in invalid:
            print(f"order status: {ord.status}")
            break
        elif ord.status in valid:
            print(f"order status: {ord.status}")
            g.data["opps"] = position.opps(g.data, api)
            g.data["qty_available"] = math.floor(
                float(position.qty_available(g.data, api))
            )
            print(f"qty_available: {g.data.get('qty_available')}")

            if g.data.get("sp") is True:
                try:
                    trailing_stop_data = TrailingStopOrderRequest(
                        symbol=g.data.get("ticker"),
                        qty=g.data.get("qty_available"),
                        side=g.data.get("opps"),
                        time_in_force=TimeInForce.DAY,
                        after_hours=g.data.get("after_hours"),
                        trail_percent=g.data.get("trail_percent"),
                        client_order_id=g.data.get("order_id") + "trailing",
                    )
                    app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

                    trailing_stop_order = api.submit_order(
                        order_data=trailing_stop_data
                    )
                    app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)

                    response_data = {
                        "message": "Webhook received and processed successfully"
                    }
                    return jsonify(response_data), 200
                except Exception as e:
                    app.logger.error("Error processing request: %s", str(e))
                    error_message = {"error": "Failed to process webhook request"}
                    return jsonify(error_message), 400
            else:
                skip_message = {"Skip": "Skip webhook"}
                return jsonify(skip_message), 204

        time.sleep(5)


# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
# @NOTE: some stocks and ETFs are not allowed to sell short in notional i.e. BKKT, EDIT,
@orders.route("/notional", methods=["POST"])
def notional():
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


@orders.route("/crypto", methods=["POST"])
def crypto():
    # Check if we should process the request
    if g.data.get("sp") is True:
        try:
            market_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                notional=g.data.get("notional"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.IOC,
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


@orders.route("/market", methods=["POST"])
def market():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.data.get("sp") is True:
        try:
            market_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.IOC,
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


@orders.before_request
def preprocess():
    """
    Add an orders before_request to handle preprocessing.
    All orders go through this preprocessor to qualify them for processing.
    This is to ensure consistency and to avoid losses.
    This is not intended to replace other order types like limit, stop, etc.
    Essentailly, it's to preprocess the Data object and set defaults before it's sent to the order endpoints.
    Keep it fast and simple......
    """
    # Hack Time
    api.get_clock()

    #

    # Set the global data to the request.json
    g.data = request.json

    # Validate the signature of the request coming in
    if sec.validate_signature(g.data) != True:
        return jsonify({"Unauthorized": "Failed to process signature"}), 401

    # Account
    g.data["acc"] = account.get_account(g.data, api)

    # Position
    g.data["pos"] = position.get_position(g.data, api)

    # Calc
    # @NOTE: qty depends on risk so we calculate risk first
    g.data["action"] = g.data.get("action", "buy")
    g.data["risk"] = g.data.get("risk", calc.risk(g.data))
    g.data["notional"] = g.data.get("notional", calc.notional(g.data))
    g.data["profit"] = g.data.get("profit", calc.profit(g.data))
    g.data["qty"] = g.data.get("qty", calc.qty(g.data))
    g.data["side"] = g.data.get("side", calc.side(g.data))
    g.data["trail_percent"] = g.data.get("trail_percent", calc.trail_percent(g.data))
    g.data["trailing"] = g.data.get("trailing", calc.trailing(g.data))

    # Order
    g.data["order_id"] = order.gen_id(g.data, 10)

    # Other
    g.data["after_hours"] = g.data.get("after_hours", False)
    g.data["comment"] = g.data.get("comment", "nocomment")
    g.data["interval"] = g.data.get("interval", "nointerval")

    # Analyze the position last after all other calculations
    g.data["sp"] = g.data.get("sp", position.sp(g.data, api))

    app.logger.debug("Data: %s", g.data)

    # Increment the counter for this specific value
    # post_data_counter.labels(data=g.data).inc()

    # Set the gauge to this specific value
    # post_data_gauge.labels(data=g.data).set(g.data)


# Add an orders after_request to handle postprocessing
@orders.after_request
def postprocess(response):
    # @TODO: this needs to spawn async trailing orders after each market order has been filled
    if (
        hasattr(g, "data")
        and response.status_code == 200
        and g.data.get("trailing") is True
    ):
        print("trailing stop order")
        # trailing()

    return response


# Add app.route for health check
@app.route("/health", methods=["GET"])
def health_check():
    return render_template("health.html"), 200


@app.route("/metrics")
def metrics_endpoint():
    return "Metrics are exposed!"


# Add app.route for 404 page
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Logs the request headers and body if debugging is on i.e. paper|dev environment
@app.before_request
def log_request_info():
    app.logger.debug("Headers: %s", request.headers)
    app.logger.debug("Body: %s", request.get_data())


#######################################################
#### APP INIT #########################################
#######################################################
if __name__ == "__main__":
    app.register_blueprint(orders)
    app.run(host="0.0.0.0", port=5000)
