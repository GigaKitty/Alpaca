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
from decimal import Decimal
from flask import Flask, Blueprint, g, request, jsonify, json, render_template
from utils import position, sec

import boto3
import json
import math
import os
import random
import requests
import string

app = Flask(__name__)
orders = Blueprint("orders", __name__)

# Generates a unique order id based on interval and strategy coming from the webhook
def generate_order_id(data, length=10):
    """
    Creates a unique order id based on interval and strategy coming from the webhook
    There is not really input validation here and could maybe use some failover but it hasn't caused any issues to date
    """
    characters = string.ascii_lowercase + string.digits
    comment = data.get("comment").lower()
    interval = data.get("interval").lower()
    order_rand = "".join(random.choice(characters) for _ in range(length))
    order_id = [comment, interval, order_rand]
    return "-".join(order_id)


# Calculates the price based on the price
def calc_price(price):
    """
    Convert to decimal obviously
    """
    return Decimal(price)


# Calculates the limit price based on the price
def calc_limit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.998


# Calculates the profit price based on the price
def calc_profit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 1.001


# Calculates the stop price based on the price
def calc_stop_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.999

def analyze_position(data, position):
    """
    Gives the hook an opportunity to justify the order or not.
    Basically if we're already in a position and there's no profit.
    Then stay in position but buy more at same side and don't switch.

    If there's no profit and the action isn't the same then we skip for same side trades.
    """
    """
    profit returns a +/- number
    """
    profit = float(position.unrealized_pl)
    # make position.side lowercase for comparison with action
    side = position.side.lower()

    # match naming convention of action
    if data.get("action") == "buy":
        action = "long"
    else:
        action = "short"

    # if we're in a position and there's no profit then we need to buy more
    if profit <= 0 and side == action:
        print(position.unrealized_pl)
        print(f"Buy {position.symbol} @ {side} side")
        return True
    # if we're in a position and there's no profit and the action is not the same to side then we skip
    elif profit <= 0 and side != action:
        print(position.unrealized_pl)
        print("Skip for same side trades")
        return False
    # if we're in a position and there's profit and the action is not the same to side then we close and continue
    elif profit >= 1 and side != action:
        print(f"Closing position {position.symbol}")
        api.close_position(position.symbol)
        print(f"Closed position {position.symbol}")
        return True
    # all else return true
    else:
        print("Continue")
        return True


# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
@orders.route("/notional", methods=["POST"])
def notional():
    """
    purchase a dollar amount of a stock or ETF based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.ap is True:
        try:
            market_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                notional=g.data.get("notional"),
                side=g.data.get("action"),
                type="market",
                time_in_force="day",
                order_id=generate_order_id(g.data, 10),
            )
            market_order = g.api.submit_order(order_data=market_order_data)

            response_data = {"message": "Webhook received and processed successfully"}

            return jsonify(response_data), 200

        except Exception as e:
            error_message = {"error": "Failed to process webhook request"}

            return jsonify(error_message), 200
    else:
        message = {"info": "g.ap is False"}
        return jsonify(message), 200


@orders.route("/market", methods=["POST"])
def order():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    if g.ap is True:
        try:
            market_order_data = MarketOrderRequest(
                symbol=g.data.get("ticker"),
                qty=g.data.get("qty"),
                side=g.data.get("action"),
                time_in_force=TimeInForce.IOC,
                client_order_id=generate_order_id(g.data, 10),
            )
            print(market_order_data)
            market_order = g.api.submit_order(order_data=market_order_data)
        except Exception as e:
            error_message = {"error": "Failed to process webhook request"}
            return jsonify(error_message), 200


#  Add an orders before_request to handle preprocessing
@orders.before_request
def preprocess():
    api.get_clock()
    data = request.json
    if sec.validate_signature(data) != True:
        return jsonify({"error": "Failed to process signature"}), 400

    pos = position.get(data)
    if pos is not False:
        ap = analyze_position(data, pos)

    elif pos is False and hasattr(data, "preference"):
        if data.get("preference") == data.get("action"):
            ap = True
    else:
        ap = True
    g.ap = ap
    g.api = api
    g.data = data


# Add an orders after_request to handle postprocessing
@orders.after_request
def postprocess(response):
    return response


# Add app.route for health check
@app.route("/health", methods=["GET"])
def health_check():
    return render_template("health.html"), 200


# Add app.route for 404 page
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.before_request
def log_request_info():
    app.logger.debug("Headers: %s", request.headers)
    app.logger.debug("Body: %s", request.get_data())


#######################################################
#### ENVIRONMENT
#######################################################
"""
 Set the environment variable COPILOT_ENVIRONMENT_NAME to main or dev
"""
paper = True if os.getenv("COPILOT_ENVIRONMENT_NAME") != "main" else False

"""
Initialize the Alpaca API
"""
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)
#######################################################
#######################################################
#######################################################

if __name__ == "__main__":
    app.register_blueprint(orders)
    app.run(host="0.0.0.0", port=5000, debug=paper)
