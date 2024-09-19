import random
import string
import os
from time import sleep
import requests
from datetime import datetime
from pytz import timezone
from config import app

tz = timezone("America/New_York")
today = datetime.now(tz).date().isoformat()


if os.getenv("ENVIRONMENT") == "main":
    BASE_URL = "https://api.alpaca.markets"

else:
    BASE_URL = "https://paper-api.alpaca.markets"

DATA_URL = "https://data.alpaca.markets/v2"


# Generates a unique order id based on interval and strategy coming from the webhook
def gen_id(data, length=10):
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


def get_orders_for_ticker(ticker):
    all_orders = []
    limit = 500
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
    end_of_day = datetime.combine(today, datetime.max.time()).isoformat() + "Z"


    headers = {
        "APCA-API-KEY-ID": os.getenv("APCA_API_KEY_ID"),
        "APCA-API-SECRET-KEY": os.getenv("APCA_API_SECRET_KEY"),
    }

    while True:
        # API request parameters
        params = {
            "symbols": ticker,
            "status": "open",
            "after": start_of_day,
            "direction": "asc",  # Sort in ascending order
            "until": end_of_day,
            "limit": limit,
        }

        url = f"{BASE_URL}/v2/orders"
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching orders: {response.content}")
            break

        orders = response.json()
        if not orders:
            break

        all_orders.extend(orders)

        end_of_day = orders[-1][
            "submitted_at"
        ]

    return all_orders
