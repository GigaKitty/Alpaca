from config import app, api, SKIP_PATHS, PREPROCESS
from flask import request, jsonify, g
from utils import sec, account, position, calc, order
from utils.performance import timeit_ns


###################
# Below is the start of preprocess functions that can be added at the webhook level.
# These functions are called before the order is processed.
###################
def buy_side_only(data):
    """
    Close all open orders for the symbol
    Do nothing if the action is sell and there is no position
    """
    if data.get("pos") is False and data.get("action") == "sell":
        response_data = {"order": "order skipped"}
        return jsonify(response_data), 200
    elif (
        data.get("pos") is not False
        and data.get("side") != data.get("action")
        and data.get("action") == "sell"
    ):
        try:
            api.close_position(data.get("ticker"))
            position.wait_position_close(data, api)
            response_data = {"order": "position closed"}
            g.data["pos"] = False
            return jsonify(response_data), 200
        except Exception as e:
            app.logger.error(f"Failed to close position for {data.get('ticker')}: {e}")
            error_message = {
                "error": f"Failed to close position for {data.get('ticker')}: {e}"
            }
            return jsonify(error_message), 400


@app.before_request
@timeit_ns
def preprocess():
    """
    Add an orders before_request to handle preprocessing.
    All orders go through this preprocessor to qualify them for processing.
    This is to ensure consistency and to avoid losses.
    This is not intended to replace other order types like limit, stop, etc.
    Essentailly, it's to preprocess the Data object and set defaults before it's sent to the order endpoints.
    Keep it fast and simple......
    """
    # Set the global data to the request.json
    g.data = request.json

    # Exit Early fail often 🦉 Validate the signature of the request coming in
    if sec.authorize(g.data) != True and request.path not in SKIP_PATHS:
        return jsonify({"Unauthorized": "Failed to process signature"}), 401

    # Skip endpoints in the list 🦘
    if request.path in SKIP_PATHS:
        return jsonify({"Skip endpoint": "🦘 Skipping from skip list"}), 400

    # Hack Time 😎
    clock = api.get_clock()

    # Reject after hours equity orders 🫷
    if not clock.is_open and (
        request.endpoint is None or request.endpoint.startswith(("equity"))
    ):
        return jsonify({"Market Closed": "📉 Market is closed for equity orders"}), 400

    if g.data not in [None, {}]:
        #####################
        # Prepare thy data 😇
        #####################
        # Static data
        g.data["acc"] = account.get_account(g.data, api)  # Setup account details
        g.data["pos"] = position.get_position(
            g.data, api
        )  # Get current position for symbol

        # Calc data
        g.data["risk"] = calc.risk(
            g.data
        )  # @NOTE: Risk needs to be calculated first before qty and notional
        
        #g.data["limit_price"] = calc.limit_price(g.data)
        g.data["notional"] = calc.notional(g.data)
        g.data["profit"] = calc.profit(g.data)
        g.data["qty_available"] = calc.qty_available(g.data, api)
        g.data["qty"] = calc.qty(g.data)
        g.data["side"] = calc.side(g.data)
        g.data["trail_percent"] = calc.trail_percent(g.data)
        g.data["trailing"] = calc.trailing(g.data)
        # Override the data object with the POST data
        g.data["opps"] = position.opps(g.data, api)
        g.data["order_id"] = order.gen_id(g.data, 10)

        g.data["after_hours"] = g.data.get("after_hours", False)
        g.data["comment"] = g.data.get("comment", "🤐")
        g.data["interval"] = g.data.get("interval", "🔕")

        # This will run some operations before the order is processed
        # Actions like closing orders, etc.
        # Preprocess functions are ran after the global data operations are done
        # and g.data.get("preprocess") in PREPROCESS
        preprocess_list = g.data.get("preprocess", [])
        if isinstance(preprocess_list, list) and any(
            item in PREPROCESS for item in preprocess_list
        ):
            for func in preprocess_list:
                if func == "buy_side_only":
                    result = buy_side_only(g.data)
                    return result

    # Uncomment to debug the data object
    # app.logger.debug("📭 Data: %s", g.data)
