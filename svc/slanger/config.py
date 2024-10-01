from alpaca.trading.client import TradingClient
from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics
from utils import metrics, logging
import os

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
api = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize the Flask app
app = Flask(__name__)


SKIP_ENDPOINTS = ['metrics_endpoint', 'health_check', 'health_check_liveness', 'health_check_readiness', 'health_check_startup']
COMMENTS = ['sl/tp', 'Close entry(s) order Long', 'Close entry(s) order Short']

# Enable debug mode if FLASK_ENV is set to development
if os.getenv('ENVIRONMENT') == 'dev' or os.getenv('DEBUG') == 'True':
    app.config['DEBUG'] = True

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Application info', version='1.0.3')


# Create a handler
#handler = logging.StreamHandler()
#handler.setLevel(logging.DEBUG)

# Create and set the custom formatter
#formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)

# Add the handler to the app's logger
#app.logger.addHandler(handler)
#app.logger.setLevel(logging.DEBUG)