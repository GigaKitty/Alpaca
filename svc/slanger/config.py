import os
from flask import Flask
from alpaca.trading.client import TradingClient
#import logging
#import coloredlogs

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize the Flask app
app = Flask(__name__)

# Enable debug mode if FLASK_ENV is set to development
if os.getenv('ENVIRONMENT') == 'dev' or os.getenv('DEBUG') == 'True':
    app.config['DEBUG'] = True

# coloredlogs.install(level='DEBUG', logger=app.logger, fmt='%(asctime)s %(levelname)s %(message)s')
# # Define a custom logging format
# formatter = ColoredFormatter(
#     "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
#     log_colors={
#         'DEBUG': 'cyan',
#         'INFO': 'green',
#         'WARNING': 'yellow',
#         'ERROR': 'red',
#         'CRITICAL': 'bold_red',
#     },
# )

# # Get the Flask app's logger and set the level
# handler = logging.StreamHandler()
# handler.setFormatter(formatter)

# # Set the handler for the Flask logger
# app.logger.addHandler(handler)
# app.logger.setLevel(logging.DEBUG)