from alpaca.trading.client import TradingClient
from flask import Flask
from utils import logging
import os

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize the Flask app
app = Flask(__name__)

SKIP_PATHS = [
    "/metrics",
    "/health",
    "/metrics_endpoint",
    "/health_check",
    "/health_check_liveness",
    "/health_check_readiness",
    "/health_check_startup",
]
PREPROCESS = ["buy_side_only", "sell_side_only"]
POSTPROCESS = ["half_supertrend"]

COMMENTS = ["sl/tp", "Close entry(s) order Long", "Close entry(s) order Short"]

# Enable debug mode if FLASK_ENV is set to development
if os.getenv("ENVIRONMENT") == "dev" or os.getenv("DEBUG") == "True":
    app.config["DEBUG"] = True