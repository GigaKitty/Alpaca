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
from utils import position, sec, order
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
                after_hours=True,
                take_profit=TakeProfitRequest(limit_price=round(price * 1.03, 2)),
                stop_loss=StopLossRequest(
                    stop_price=round(price * 0.98, 2),
                    limit_price=round(price * 0.97, 2),
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
                side=g.data.get("action"),
                time_in_force="gtc",
                after_hours=True,
                trail_percent=float(g.data.get("trailing")),
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


# order type to "wiggle" out of a position that's losing over time triggered via TradingView WebHook
# This strategy once it's existed a position it will not enter another one.
@orders.route("/wiggle", methods=["POST"])
def wiggle():
    """
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    # Get the current position for this symbol
    pos = position.get(g.data, api)

    # If we don't have a position we exit because we only wanted out and don't want back in if it receives another signal.
    if pos is False:
        return jsonify({"error": "No position to wiggle out of"}), 204

    if g.data.get("sp") is True:
        try:
            market_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.DAY,
                client_order_id=g.data.get("order_id") + "_" + "wiggle",
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
                after_hours=True,
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
                after_hours=True,
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

    # Check if we have a position
    pos = position.get(g.data, api)
    app.logger.debug("Position: %s", pos)

    # Generate and add order_id to the g.data object
    g.data["order_id"] = order.gen_id(g.data, 10)
    app.logger.debug("Order ID: %s", g.data["order_id"])

    # % to trail on the order this can be set in the request coming from TradingView
    g.data["trailing"] = g.data.get("trailing", 4.20)

    # This is a $ amount selloff threshold that we would like to make before exiting.
    g.data["threshold"] = g.data.get("threshold", 10)

    # Set a default qty of 10 contracts
    g.data["qty"] = g.data.get("qty", 10)

    # Set a default notional of 1000
    g.data["notional"] = g.data.get("notional", 10)

    # Set default preference to both user can also specify buy|sell
    g.data["preference"] = g.data.get("preference", "both")

    # If we have a position we need to analyze it and make sure it's on the side we want
    if pos is not False:
        g.data["sp"] = position.anal(api, g.data, pos)
    # If we don't have a position then we can check if there's a preference for buy|sell|both & short|long and act accordingly
    elif pos is False:
        if (
            g.data.get("preference") == g.data.get("action")
            or g.data.get("preference") == "both"
        ):
            g.data["sp"] = True
    # If we don't have a position and there's no preference then we can set the g.data["sp"] to True
    else:
        g.data["sp"] = True

    app.logger.debug("Data: %s", g.data)


# Add an orders after_request to handle postprocessing
# @orders.after_request
# def postprocess(response):
#    return response


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
