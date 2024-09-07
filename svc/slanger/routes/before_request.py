from config import app, api
from flask import request, jsonify, g
from utils import sec, account, position, calc, order

SKIP_ENDPOINTS = ['metrics_endpoint', 'health_check', 'health_check_liveness', 'health_check_readiness', 'health_check_startup']

@app.before_request
def preprocess():
    """
    Add an orders before_request to handle preprocessing.
    All orders go through this preprocessor to qualify them for processing.
    This is to ensure consistency and to avoid losses.
    This is not intended to replace other order types like limit, stop, etc.
    Essentailly, it's to preprocess the Data object and set defaults before it's sent to the order endpoints.
    Keep it fast and simple......
    """
    app.logger.debug("Headers: %s", request.headers)
    app.logger.debug("Body: %s", request.get_data())

    # Skip endpoints in the list
    if request.endpoint in SKIP_ENDPOINTS:
        return
    
    # Hack Time
    clock = api.get_clock()

    # Reject after hours orders
    if not clock.is_open and not request.endpoint.startswith('crypto'):
        return jsonify({"Market Closed": "Market is closed"}), 400
    
    # Set the global data to the request.json
    g.data = request.json

    # Validate the signature of the request coming in
    if sec.validate_signature(g.data) != True:
        return jsonify({"Unauthorized": "Failed to process signature"}), 401

    # Setup account details
    g.data["acc"] = account.get_account(g.data, api)

    # Get current position for symbol
    g.data["pos"] = position.get_position(g.data, api)

    # @NOTE: qty and notional depend on risk so we calculate risk first
    g.data["action"] = g.data.get("action", "buy")
    g.data["limit_price"] =  round(calc.limit_price(g.data), 2)
    g.data["risk"] = g.data.get("risk", calc.risk(g.data))
    g.data["notional"] = g.data.get("notional", calc.notional(g.data))
    g.data["profit"] = g.data.get("profit", calc.profit(g.data)) 
    g.data["qty"] = g.data.get("qty", calc.qty(g.data))
    g.data["qty_available"] = g.data.get("qty_available", calc.qty_available(g.data, api))
    g.data["side"] = g.data.get("side", calc.side(g.data))
    g.data["trail_percent"] = g.data.get("trail_percent", calc.trail_percent(g.data))
    g.data["trailing"] = g.data.get("trailing", calc.trailing(g.data))

    # Order
    g.data["order_id"] = order.gen_id(g.data, 10)

    # Other
    g.data["after_hours"] = g.data.get("after_hours", False)
    g.data["comment"] = g.data.get("comment", "nocomment")
    g.data["interval"] = g.data.get("interval", "nointerval")

    # At the end so we can see the results
    #app.logger.debug("Data: %s", g.data)

    # Needs to be last
    if g.data.get("sp") != "skip":
        g.data["sp"] = g.data.get("sp", position.sp(g.data, api))
