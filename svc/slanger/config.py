from alpaca.trading.client import TradingClient
from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics
import os

# Initialize the Flask app
app = Flask(__name__)
metrics = PrometheusMetrics(app)
metrics.info("app_info", "Application info", version="1.0.3")

SKIP_PATHS = [
    "/favicon.ico",
    "/health_check_liveness",
    "/health_check_readiness",
    "/health_check_startup",
    "/health_check",
    "/health",
    "/metrics_endpoint",
    "/metrics",
]
# PRE and POST process lists are included here so that only they are able to run instead of other functions not included in the list
PREPROCESS = ["buy_side_only", "sell_side_only"]
POSTPROCESS = ["trailing_stop", "half_supertrend"]

COMMENTS = ["sl/tp", "Close entry(s) order Long", "Close entry(s) order Short"]

# Enable debug mode if FLASK_ENV is set to development
if os.getenv("ENVIRONMENT") == "dev" or os.getenv("DEBUG") == "True":
    print("DEBUG MODE ENABLED")
    #app.config["DEBUG"] = True

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)
