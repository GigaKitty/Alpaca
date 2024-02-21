from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
    TrailingStopOrderRequest,
)

from botocore.exceptions import ClientError
from flask import Flask, Blueprint, g, request, jsonify, json, render_template


from utils import position, sec, order

import boto3
import json
import os
import random
import requests
import string
import random
import string


#######################################################
#### ENVIRONMENT ######################################
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


# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
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
    But is intended to be used seperately as a tool to manage the portfolio.
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

    # Generate a unique order id
    order_id = order.generate_id(g.data, 10)
    app.logger.debug("Order ID: %s", order_id)
    # Add order_id to the data object
    g.data["order_id"] = order_id

    # This is a dollar amount selloff threshold that we would like to make before exiting.
    g.data["threshold"] = g.data.get("threshold", 10)

    # If we have a position we need to analyze it and make sure it's on the side we want
    if pos is not False:
        g.data["sp"] = position.anal(api, g.data, pos)
    # If we don't have a position then we can check if there's a preference for buy/sell & short/long and act accordingly
    elif pos is False and hasattr(g.data, "preference"):
        if g.data.get("preference") == g.data.get("action"):
            g.data["sp"] = True
    # If we don't have a position and there's no preference then we can set the g.ap to True
    else:
        g.data["sp"] = True

    app.logger.debug("Data: %s", g.data)
    app.logger.debug("AP: %s", g.ap)


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
#### APP ##############################################
#######################################################
if __name__ == "__main__":
    app.register_blueprint(orders)
    app.run(host="0.0.0.0", port=5000, debug=paper)
