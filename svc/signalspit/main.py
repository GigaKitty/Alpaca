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
import json
import os
import random
import random
import requests
import string
import string

#######################################################
#### ENVIRONMENT SETUP ################################
#######################################################
"""
 Set the environment variable COPILOT_ENVIRONMENT_NAME to main or dev
"""
paper = True if os.getenv("COPILOT_ENVIRONMENT_NAME", "dev") != "main" else False

"""
Initialize the Alpaca API
If it's dev i.e. paper trading then it uses the paper trading API
"""
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize the Flask app
app = Flask(__name__)

# Initialize the Blueprint for the orders
orders = Blueprint("orders", __name__)
#######################################################
#######################################################
#######################################################


@orders.route("/bracket", methods=["POST"])
def bracket():
    if g.data.get("sp") is True:

        try:
            # Price value is coming through the webhook from tradingview so it might not be accurate to realtime price
            price = round(float(g.data.get("price")), 2)

            bracket_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force="gtc",
                order_class=OrderClass.BRACKET,
                after_hours=g.data.get("after_hours"),
                take_profit=TakeProfitRequest(
                    limit_price=round(price * calc.limit_price(), 2)
                ),
                stop_loss=StopLossRequest(
                    stop_price=round(calc.stop_price, 2),
                    limit_price=round(calc.limit_price, 2),
                ),
                client_order_id=g.data.get("order_id") + "_" + "bracket",
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


# Trailing Percent Stop Order Type
@orders.route("/trailing", methods=["POST"])
def trailing():
    """
    Places a trailing stop order based on TradingView WebHook
    for now it only works with the trailing stop percentage
    that's to simplify the process and avoid losses due to complexity of the trailing stop order types i.e. trail_price, trail_percent, etc.
    @SEE: https://docs.alpaca.markets/v1.1/docs/working-with-orders#submitting-trailing-stop-orders
    """
    if g.data.get("sp") is True:
        try:
            trailing_stop_data = TrailingStopOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=position.opps(g.data),
                time_in_force="gtc",
                after_hours=g.data.get("after_hours"),
                trail_percent=g.data.get("trail_percent"),
                client_order_id=g.data.get("order_id") + "_" + "trailing",
            )
            app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

            trailing_stop_order = api.submit_order(order_data=trailing_stop_data)
            app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)

            response_data = {"message": "Webhook received and processed successfully"}
            return jsonify(response_data), 200

        except Exception as e:
            app.logger.error("Error processing request: %s", str(e))
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 400
    else:
        skip_message = {"Skip": "Skip webhook"}
        return jsonify(skip_message), 204


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
                client_order_id=g.data.get("order_id") + "_" + "notional",
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
                client_order_id=g.data.get("order_id") + "_" + "market",
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
    """
    # Hack Time
    api.get_clock()

    # Set the global data to the request.json
    g.data = request.json

    # Validate the signature of the request coming in
    if sec.validate_signature(g.data) != True:
        return jsonify({"Unauthorized": "Failed to process signature"}), 401

    # Check if we have a position and an account
    g.data["pos"] = position.get(g.data, api)
    g.data["acc"] = account.get(g.data, api)

    g.data["after_hours"] = g.data.get("after_hours", False)
    g.data["comment"] = g.data.get("comment", "nocomment")
    g.data["interval"] = g.data.get("interval", "nointerval")
    g.data["notional"] = g.data.get("notional", calc.notional(api))
    g.data["order_id"] = order.gen_id(g.data, 10)
    g.data["profit"] = g.data.get("profit", calc.profit(api, g.data))
    g.data["qty"] = g.data.get("qty", calc.qty(api))
    g.data["side"] = g.data.get("side", calc.side(api))

    # @TODO: update this to calc
    g.data["sp"] = g.data.get("sp", position.sp(api, g.data))

    g.data["trail_percent"] = g.data.get("trail_percent", 0.1)
    g.data["trailing"] = g.data.get("trailing", calc.trailing(api))
    g.data["wiggle"] = g.data.get("wiggle", calc.wiggle(api, g.data))

    app.logger.debug("Data: %s", g.data)


# Add an orders after_request to handle postprocessing
@orders.after_request
def postprocess(response):
    # If trailing is active and we have a position then we place a traillng order for the current position size
    if (
        response.status_code == 200
        and g.data.get("trailing") is True
        and position.get(g.data, api) is not False
    ):
        # Gets the updated position again after new order is placed
        g.data["pos"] = position.get(g.data, api)
        # Trigger trailing stop order
        trailing()

    return response


# Add app.route for health check
@app.route("/health", methods=["GET"])
def health_check():
    return render_template("health.html"), 200


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
    app.run(host="0.0.0.0", port=5000, debug=paper)
