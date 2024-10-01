from config import app, api
from flask import request, jsonify, g
from utils import sec, account, position, calc, order
from config import SKIP_ENDPOINTS

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

    # Reject after hours equity orders
    if not clock.is_open and (request.endpoint is None or request.endpoint.startswith(('equity'))):
        return jsonify({"Market Closed": "Market is closed or order is not valid"}), 400
    
    # Set the global data to the request.json
    g.data = request.json

    # Validate the signature of the request coming in
    if sec.validate_signature(g.data) != True and request.endpoint not in ['health', 'metrics']:
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
    g.data["trailing"] = calc.trailing(g.data)
    g.data["opps"] = g.data.get("opps", position.opps(g.data, api))
    
    #@TODO make this an option
    g.data["entry_interval"] = g.data.get("entry_interval", "1m")
    g.data["exit_interval"] = g.data.get("exit_interval", "1m")

    # Order
    g.data["order_id"] = order.gen_id(g.data, 10)
    g.data["order_entry_interval"] = g.data.get("order_entry_interval", "1m")

    # Other
    g.data["after_hours"] = g.data.get("after_hours", False)
    g.data["comment"] = g.data.get("comment", "nocomment")
    g.data["interval"] = g.data.get("interval", "nointerval")

    # At the end so we can see the results
    #app.logger.debug("Data: %s", g.data)

    # Needs to be last so we can see the results
    # skip sp if reverse type order
    # @TODO: make this a whitelist instead of a blacklist
    #if g.data.get("sp") != "skip" or request.endpoint not in ['reverse', 'trailing', 'tieredfiblimit']:
      #  g.data["sp"] = g.data.get("sp", position.sp(g.data, api))

