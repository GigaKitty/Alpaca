from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest, TrailingStopOrderRequest
from botocore.exceptions import ClientError
from decimal import Decimal
from flask import Flask, request, jsonify, json
from pyngrok import ngrok

import boto3
import json
import math
import os
import random
import requests
import string

###############################################
###############################################
###############################################
# Get the secrets
def get_secrets():
    """
    This will allow us to pull secrets from aws to run locally or in the cloud.
    Portable solution with minimal overhead on architecture.
    Simply works...
    """

    # @TODO: make this dynamic for dev|prod i.e. paper|live
    secret_name = "alpaca-tradingview"
    # @TODO: make this dynamic for region ( no need for multi-region or anything fancy )
    region_name = "us-west-2"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


###############################################
###############################################
###############################################
# Define the secrets that are pulled from AWS.
# @NOTE: we are not going to use an .env file for anything and all secrets will be pulled from Secrets Manager
secrets = get_secrets()
api = TradingClient(secrets.get('APCA_API_KEY_ID'),
                    secrets.get('APCA_API_SECRET_KEY'), paper=True)
signature = secrets.get('TRADINGVIEW_SECRET')

###############################################
###############################################
###############################################
# Initialize the APP
app = Flask(__name__)


def validate_signature(data):
    """
    Validates a simple field value in the webhook to continue processing webhook otherwise fails.
    This isn't the most elegant solution but it adds some safety controls to arbitrary requests.
    We can further improve upon this by validating the request is legitimately coming from TradingView using SSL and/or at least IP
    """
    if (signature != data.get('signature')):
        error_message = {"error": "Signature Failed to Authorize"}
        return jsonify(error_message), 400
    else:
        return True


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


def calc_price(price):
    """
    Convert to decimal obviously
    """
    return Decimal(price)


def calc_limit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.998


def calc_profit_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 1.001


def calc_stop_price(price):
    """
    @TODO: make the arg calc the tolerance
    """
    return float(price) * 0.999


def sync_data(data):
    """
    Sync the clock so that we don't get an error from the data request.
    Set the data var and return it
    """
    api.get_clock()
    data = request.json
    return data


def calc_contract_size(data):
    """
    Dumb way to calculate contract size based on interval.
    Lower contract(s) for lower intervals so minimize risk and orders cross comtaminating into losses.
    # @SEE: https://en.wikipedia.org/wiki/Fibonacci_sequence
    # @WHY: because it's funner this way
    """
    if (data.get('interval') == 'S'):
        contracts = 2
    elif (data.get('interval') == '30S'):
        contracts = 3
    elif (data.get('interval') == '1'):
        contracts = 5
    elif (data.get('interval') == '5'):
        contracts = 8
    elif (data.get('interval') == '15'):
        contracts = 13
    elif (data.get('interval') == '30'):
        contracts = 21
    else:
        contracts = 1

    return contracts


def get_position(data):
    """
    Checks the position of the current ticker
    """
    try:
        return api.get_open_position(data.get('ticker'))
    except Exception as e:
        return False


def smash_or_pass(data, position):
    """
    Gives the hook an opportunity to justify the order or not.
    Basically if we're already in a position and there's no profit.
    Then stay in position but buy more at same side and don't switch.

    If there's no profit and the action isn't the same then we skip for better trades.
    """
    profit = math.copysign(1, float(position.unrealized_pl))
    #  qty = math.copysign(1,float(position.qty))
    print('--------------------------------profit')
    print(profit)
    print('--------------------------------position')
    print(position)

    if data.get('action') == 'buy':
        action = 'long'
    else:
        action = 'short'

    print(action)

    if (profit <= 0 and position.side == action):
        print(position.unrealized_pl)
        toggle_light_position(data, profit)
        print("Buy more to creep!")
        return True
    elif (profit <= 0 and position.side != action):
        print(position.unrealized_pl)
        toggle_light_position(data, profit)
        print("Skip")
        return False
    elif (profit > 0 and position.side != action):
        print('Close & Continue')
        # @TODO: toggle off when closed
        api.close_position(data.get('ticker'))
        toggle_light_position(data, profit)
        print('Closed positions')
        return True
    else:
        print("Continue")
        return True

def toggle_light_position(data, profit):
    """
    Tap into our lifx power to visually keep track of order status
    @TODO: make this an async function that just checks positions at intervals instead of on order request
    Simply adds green/red for status
    To configure rename light(s) to TICKER names
    """
    headers = {
        "Authorization": "Bearer %s" % secrets.get('LIFX_TOKEN'),
    }

    if (profit >= 0):
        color = "green saturation:1"
    elif (profit < 0):
        color = "red saturation:1"

    label = "label:" + data.get('ticker')
    
    payload = {
      "states": [
        {
            "selector" : label,
            "hue": 0,
            "color": color,
            "brightness": 1
        }
      ],
      "defaults": {
        "power": "on",
        "saturation": 0,
        "duration": 2.0
        }
    }

    response = requests.put('https://api.lifx.com/v1/lights/states', data=json.dumps(payload), headers=headers)


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
            contracts = calc_contract_size(data)
            order_id = generate_order_id(data, 10)
            ticker = data.get('ticker')
            # supports ioc|gtc
            time_in_force = "ioc"

            print(f"Data: {data}")

            #  Setup Price
            price = calc_price(data.get('price'))
            print(f"Price: ${price}USD")
            print(f"Order ID: {order_id}")

            # Setup position
            position = get_position(data)
            if position is not False:
                sp = smash_or_pass(data, position)
            else:
                sp = True

            if sp is True:
                print('!--------------------------------------Posting order')
                print(data)
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
            else:
                print(f"Skipping the order of {contracts} @ ${price}USD ")

            response_data = {
                "message": "Webhook received and processed successfully"}

            return jsonify(response_data), 200

        except Exception as e:

            error_message = {"error": "Failed to process webhook request"}

            return jsonify(error_message), 400


@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


if __name__ == '__main__':
    # Start ngrok tunnel with authentication token and custom domain
    ngrok.set_auth_token(secrets.get('NGROK_AUTH_TOKEN'))
    public_url = ngrok.connect(
        5000, hostname=secrets.get('CUSTOM_DOMAIN')).public_url
    print(f"ngrok tunnel URL: {public_url}")
    app.run(host='0.0.0.0', port=5000)
