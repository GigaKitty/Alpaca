from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest, TrailingStopOrderRequest
from decimal import Decimal
from dotenv import load_dotenv
from flask import Flask, request, jsonify, json
from pyngrok import ngrok
from botocore.exceptions import ClientError

import argparse
import os
import random
import string
import math
import boto3
import json

###############################################
###############################################
###############################################
# Get the secrets


def get_secrets():
    """
    This will allow us to pull secrets from aws to run locally or in the cloud.
    """

    # @TODO: make this dynamic for dev|prod i.e. paper|live
    secret_name = "alpaca-tradingview"
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
# Define the secrets
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
    Validates a simple field value in the webhook to continue processing webhook otherwise fails
    """
    if (signature != data.get('signature')):
        error_message = {"error": "Signature Failed to Authorize"}
        return jsonify(error_message), 400
    else:
        return True


def generate_order_id(data, length=10):
    """
    Creates a unique order id based on interval and strategy coming from the webhook
    """
    characters = string.ascii_lowercase + string.digits
    comment = data.get('comment').lower()
    interval = data.get('interval').lower()
    order_rand = ''.join(random.choice(characters) for _ in range(length))
    order_id = [comment, interval, order_rand]
    return "-".join(order_id)


def calc_price(price):
    return Decimal(price)


def calc_limit_price(price):
    return float(price) * 0.998


def calc_profit_price(price):
    return float(price) * 1.001


def calc_stop_price(price):
    return float(price) * 0.999


def sync_data(data):
    api.get_clock()
    data = request.json
    return data


def sanitize_order(data):
    return data


def calc_contract_size(data):
    """
    Dumb way to calculate contract size based on interval.
    Lower contract(s) for lower intervals so minimize risk and orders cross comtaminating into losses.
    """
    if (data.get('interval') == 'S'):
        contracts = 1
    elif (data.get('interval') == '30S'):
        contracts = 3
    elif (data.get('interval') == '1M'):
        contracts = 5
    elif (data.get('interval') == '5M'):
        contracts = 7
    elif (data.get('interval') == '15M'):
        contracts = 9
    elif (data.get('interval') == '30M'):
        contracts = 11

    return contracts


def get_position(data):
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
        print("Buy more to creep!")
        return True
    elif (profit <= 0 and position.side != action):
        print(position.unrealized_pl)
        print("Skip")
        return False
    elif (profit > 0 and position.side != action):
        print('Close & Continue')
        closed = api.close_position(data.get('ticker'))
        print(closed)
        print('Closed positions')
        return True
    else:
        print("Continue")
        return True


#  @app.route('/alpaca_trailing_stop_order', methods=['POST'])
#  def trailing_stop():
#      """
#      Places a simple Trailling Stop order or BUY or SELL based on TraingView WebHook
#      @SEE: https://alpaca.markets/docs/trading/getting_started/how-to-orders/#submitting-trailing-stop-orders
#      """
#      data = sync_data(request.json)
#
#      if (validate_signature(data) == True):
#          try:
#              action = data.get('action')
#              contracts = calc_contract_size(data)
#              order_id = generate_order_id(data, 10)
#              ticker = data.get('ticker')
#              # supports ioc|gtc
#
#              print(f"Data: {data}")
#
#              #  Setup Price
#              price = calc_price(data.get('price'))
#              print(f"Price: ${price}USD")
#              print(f"Order ID: {order_id}")
#
#              trailing_percent_data = TrailingStopOrderRequest(
#                  symbol=ticker,
#                  qty=contracts,
#                  side=action,
#                  time_in_force=TimeInForce.GTC,
#                  trail_percent=1.00 # hwm * 0.99
#              )
#
#              trailing_percent_order = api.submit_order(
#                  order_data=trailing_percent_data
#              )
#
#              response_data = {"message": "Webhook received and processed successfully"}
#
#              return jsonify(response_data), 200
#
#          except Exception as e:
#
#              error_message = {"error": "Failed to process webhook request"}
#
#              return jsonify(error_message), 400
#

@app.route('/alpaca_market_order', methods=['POST'])
def market():
    """
    Places a simple market order or BUY or SELL based on TraingView WebHook
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
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=contracts,
                    side=action,
                    time_in_force=time_in_force,
                    client_order_id=order_id
                )
                market_order = api.submit_order(
                    order_data=market_order_data
                )
            else:
                print('Skipping the order')

            response_data = {
                "message": "Webhook received and processed successfully"}

            return jsonify(response_data), 200

        except Exception as e:

            error_message = {"error": "Failed to process webhook request"}

            return jsonify(error_message), 400


@app.route('/alpaca_debug_order', methods=['POST'])
def debug():
    data = sync_data(request.json)

    if (validate_signature(data) == True):
        try:
            position = get_position(data)
            if position is not False:
                sp = smash_or_pass(data, position)
            else:
                sp = True

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
