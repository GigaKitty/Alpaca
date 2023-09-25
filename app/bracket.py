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


# preparing bracket order with both stop loss and take profit
bracket__order_data = MarketOrderRequest(
                    symbol="QQQ",
                    qty=1,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(400),
                    stop_loss=StopLossRequest(300)
                    )

bracket_order = trading_client.submit_order(
                order_data=bracket__order_data
               )
