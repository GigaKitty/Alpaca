# A silly script to randomly buy or sell a symbol based on what the gods of random say.
from datetime import datetime, timedelta
from dotenv import load_dotenv
from progress.bar import Bar
from time import sleep

import alpaca_trade_api as tradeapi
import math, random, time, os, argparse


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Load environment variables from .env file')
parser.add_argument('--dotenv', type=str, help='Path to .env file')
args = parser.parse_args()

# Alpaca API credentials
load_dotenv(dotenv_path=args.dotenv)

# Initialize Alpaca API
api = tradeapi.REST(os.getenv('APCA_API_KEY_ID'), os.getenv('APCA_API_SECRET_KEY'), base_url=os.getenv('APCA_API_BASE_URL'))
symbol = os.getenv('SYMBOL')

# Same as the function in the random version
def get_position(symbol):
    positions = api.list_positions()
    for p in positions:
        if p.symbol == symbol:
            return float(p.qty)
    return

while True:
    api.get_clock()

    position = get_position(symbol)
    # 1 - 1000 Seconds
    sleeper=random.randint(1, 86400)
    # 1 - 100 $USD
    notional=random.randint(1, 100)

    # SCIENTIFICALLY CHECK IF WE SHOULD BUY OR SELL
    gods_say = random.choice(['buy', 'sell'])
    print(f"Holding: {position} / Gods: {gods_say}")
    print(f'The GODS HAVE SPOKEN Symbol: {symbol} / Side: {gods_say} / Quantity: ${notional} USD')
    api.submit_order(
        symbol=symbol,
        notional=notional,
        side=gods_say,
        type='market',
        time_in_force='gtc'
        )
    print('Lets wait for the gods to manifest again...')
    print(f"Waiting for {sleeper} seconds")
    with Bar('😴') as bar:
        for i in range(100):
            sleep(sleeper/100)
            bar.next()
