from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest, TrailingStopOrderRequest
from botocore.exceptions import ClientError
from decimal import Decimal
from flask import Flask, Blueprint, g, request, jsonify, json, render_template


import boto3
import json
import math
import os
import random
import requests
import string


# Check if we're in paper or main i.e. dev or prod
def check_paper_environment():
    """
    Add a function that checks COPILOT_ENVIRONMENT_NAME and sets paper=True if it's not main and false if it is
    This will allow us to run the same code in main|dev
    """
    environment_name = os.getenv('COPILOT_ENVIRONMENT_NAME')
    if environment_name != 'main':
        return True
    else:
        return False

paper = check_paper_environment()

api = TradingClient(os.getenv('APCA_API_KEY_ID'),
                    os.getenv('APCA_API_SECRET_KEY'), paper=paper)

signature = os.getenv('TRADINGVIEW_SECRET')

orders = Blueprint('orders', __name__)
app = Flask(__name__)

# Validates the signature from TradingView
# @TODO: This should be updated to check SSL and/or IP so we can remove signature from the webhook
def validate_signature(data):
    """
    Validates a simple field value in the webhook to continue processing webhook otherwise fails.
    This isn't the most elegant solution but it adds some safety controls to arbitrary requests.
    We can further improve upon this by validating the request is legitimately coming from TradingView using SSL and/or at least IP
    """
    if (signature != data.get('signature')):
        return redirect('/404')  # Redirect to the 404 page
    else:
        return True
    
# Generates a unique order id based on interval and strategy coming from the webhook
def generate_order_id(data, length=10):
    """
    Creates a unique order id based on interval and strategy coming from the webhook
    There is not really input validation here and could maybe use some failover but it hasn't caused any issues to date
    """
    characters = string.ascii_lowercase + string.digits
    comment = data.get('comment').lower()
    interval = data.get('interval').lower()
    order_rand = ''.join(random.choice(characters) for _ in range(length))
    order_id = [comment, interval, order_rand]
    return "-".join(order_id)

# Syncs the clock so that we don't get an error from the data request
def sync_data(data):
    """
    Sync the clock so that we don't get an error from the data request.
    Set the data var and return it
    """
    api.get_clock()
    data = request.json
    return data

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

# Calculates the buying power for the account
def calc_buying_power():
    # Get our account information.
    account = api.get_account()
    
    # Check if our account is restricted from trading.
    if account.trading_blocked:
        print('Account is currently restricted from trading.')

    # Check how much money we can use to open new positions.
    print('${} is available as buying power.'.format(account.buying_power))
    
    return account.buying_power

# Gets currently open position for ticker
def get_position(data):
    """
    Checks the position of the current ticker
    """
    try:
        return api.get_open_position(data.get('ticker'))
    except Exception as e:
        return False


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

    print(float(position.unrealized_pl))
    print(f"Profit: {profit}")
    print(f"Position: {position}")

    # match naming convention of action
    if data.get('action') == 'buy':
        action = 'long'
    else:
        action = 'short'

    # if we're in a position and there's no profit then we need to buy more  
    if (profit <= 0 and side == action):
        print(position.unrealized_pl)
        print("Buy more to creep!")
        return True
    # if we're in a position and there's no profit and the action is not the same to side then we skip
    elif (profit <= 0 and side != action):
        print(position.unrealized_pl)
        print("Skip")
        return False
    # if we're in a position and there's profit and the action is not the same to side then we close and continue
    elif (profit >= 1 and side != action):
        print('Close & Continue')
        api.close_position(data.get('ticker'))
        print('Closed positions')
        return True
    # all else return true
    else:
        print("Continue")
        return True


@orders.before_request
def preprocess():
    api.get_clock()
    data = request.json

    if (validate_signature(data) != True):
        return jsonify({"error": "Failed to process signature"}), 400
    
    position = get_position(data)
    if position is not False:
        ap = analyze_position(data, position)
    else:
        ap = True

    g.ap = ap
    g.data = data

# Dollar amount to trade. Cannot work with qty. Can only work for market order types and time_in_force = day.
@orders.route('/notional', methods=['POST'])
def notional():
    market_order_data = MarketOrderRequest(
        order = api.submit_order(
        symbol=g.data.get('ticker'),
        notional=g.data.get('notional'),
        side=g.data.get('action'),
        type='market',
        time_in_force='day'
    )
    return order

@app.route('/alpaca_market_order', methods=['POST'])
def order():
    """
    Places a simple market order or BUY or SELL based on TradingView WebHook
    @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#place-new-orders
    """
    data = sync_data(request.json)
    
    if (validate_signature(data) == True):
        try:
            action = data.get('action')
            contracts = data.get('contracts')
            order_id = generate_order_id(data, 10)
            ticker = data.get('ticker')
            time_in_force = "ioc" # supports ioc|gtc

            print(f"Data: {data}")

            #  Setup Price
            price = calc_price(data.get('price'))

            # check if there's a current position
            position = get_position(data)
            ##########################################
            # if we have a position then we need to figure out what to do with it.
            if position is not False:
                ap = analyze_position(data, position)
            else:
                ap = True
    
            if ap is True:
                print(f"Placing {order_id} {action} order for {contracts} contracts on ${ticker} @ ${price}USD ")
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=contracts,
                    side=action,
                    time_in_force=TimeInForce.IOC,
                    client_order_id=order_id
                )
                print(market_order_data)
                market_order = api.submit_order(
                    order_data=market_order_data
                )
                print(market_order)
            ############################################################################
            response_data = {"message": "Webhook received and processed successfully"}

            return jsonify(response_data), 200

        except Exception as e:

            error_message = {"error": "Failed to process webhook request"}

            return jsonify(error_message), 400

# Add app.route for health check
@app.route('/health', methods=['GET'])
def health_check():
    return render_template('health.html'), 200

# Add app.route for 404 page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.before_request
def log_request_info():
    #app.logger.debug('Headers: %s', request.headers)
    #app.logger.debug('Body: %s', request.get_data())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=paper)