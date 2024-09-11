from config import app
from flask import Flask, render_template, request

# Import default routes
from routes import health, before_request, after_request, error_handler

# Import routes for crypto
from routes.crypto.limit import crypto_limit
from routes.crypto.market import crypto_market
from routes.crypto.notional import crypto_notional
from routes.crypto.stop_limit import crypto_stop_limit

# Import routes for equity
from routes.equity.bracket import equity_bracket
from routes.equity.limit import equity_limit
from routes.equity.market import equity_market
from routes.equity.notional import equity_notional
from routes.equity.stop_limit import equity_stop_limit
from routes.equity.reverse import equity_reverse
from routes.equity.reverselimit import equity_reverselimit
from routes.equity.tieredfib import equity_tieredfib

if __name__ == "__main__":
    # Register routes for crypto
    app.register_blueprint(crypto_limit, url_prefix='/crypto')
    app.register_blueprint(crypto_market, url_prefix='/crypto')
    app.register_blueprint(crypto_notional, url_prefix='/crypto')
    app.register_blueprint(crypto_stop_limit, url_prefix='/crypto')

    # Register routes for equity
    app.register_blueprint(equity_bracket, url_prefix='/equity')
    app.register_blueprint(equity_limit, url_prefix='/equity')
    app.register_blueprint(equity_market, url_prefix='/equity')
    app.register_blueprint(equity_notional, url_prefix='/equity')
    app.register_blueprint(equity_reverse, url_prefix='/equity')
    app.register_blueprint(equity_reverselimit, url_prefix='/equity')
    app.register_blueprint(equity_stop_limit, url_prefix='/equity')
    app.register_blueprint(equity_tieredfib, url_prefix='/equity')
    
    # Run the app
    app.run(host="0.0.0.0", port=5000)