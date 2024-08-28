import os
from flask import Flask
from alpaca.trading.client import TradingClient


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