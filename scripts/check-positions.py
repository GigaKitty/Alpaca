from alpaca.trading.client import TradingClient

from dotenv import load_dotenv

#  import alpaca_trade_api as tradeapi
import argparse, os, random, string, math 

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Load environment variables from .env file')
parser.add_argument('--dotenv', type=str, help='Path to .env file')
args = parser.parse_args()

# Alpaca API credentials
load_dotenv(dotenv_path=args.dotenv)

api = TradingClient(os.getenv('APCA_API_KEY_ID'), os.getenv('APCA_API_SECRET_KEY'), paper=True)

# Get our position in AAPL.
position = api.get_open_position('SPY')
profit = math.copysign(1,float(position.unrealized_pl))
print(position.side)

print('checking positions')
if (profit > 0):
    print(position.unrealized_pl)
else:
    print('skipping you will lose money')


# Get a list of all of our positions.
#  portfolio = api.get_all_positions()

# Print the quantity of shares for each position.
#  for position in portfolio:
    #  print("{} shares of {}".format(position.qty, position.symbol))
