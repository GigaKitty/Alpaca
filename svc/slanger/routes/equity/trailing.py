
from flask import Blueprint, jsonify, g
from alpaca.trading.requests import TrailingStopOrderRequest
from alpaca.trading.enums import TimeInForce
from config import api, app
# @orders.route("/trailing", methods=["POST"])
# def trailing():
#     """
#     Places a trailing stop order based on TradingView WebHook for now it only works with the trailing stop percentage that's to simplify the process and avoid losses due to complexity of the trailing stop order types i.e. trail_price, trail_percent, etc.
#     @SEE: https://docs.alpaca.markets/v1.1/docs/working-with-orders#submitting-trailing-stop-orders
#     """
#     print(f"setting up trailing stop order")
#     print(g.data)
#     #return jsonify({"message": "trailing is there and firing"}), 200
#     max_attempts = 10
#     for attempt in range(max_attempts):
#         if attempt > max_attempts:
#             print("were maxed out")
#             return False

#         ord = api.get_order_by_client_id(g.data.get("order_id"))

#         # Define the possible values for ord.status
#         invalid = {"canceled", "expired", "replaced", "pending_cancel"}
#         valid = {"filled", "partially_filled"}

#         if ord.status in invalid:
#             print(f"order status: {ord.status}")
#             break
#         elif ord.status in valid:
#             print(f"order status: {ord.status}")
#             g.data["opps"] = position.opps(g.data, api)
#             g.data["qty_available"] = math.floor(
#                 float(position.qty_available(g.data, api))
#             )
#             print(f"qty_available: {g.data.get('qty_available')}")

#             if g.data.get("sp") is True:
#                 try:
#                     trailing_stop_data = TrailingStopOrderRequest(
#                         symbol=g.data.get("ticker"),
#                         qty=g.data.get("qty_available"),
#                         side=g.data.get("opps"),
#                         time_in_force=TimeInForce.DAY,
#                         after_hours=g.data.get("after_hours"),
#                         trail_percent=g.data.get("trail_percent"),
#                         client_order_id=g.data.get("order_id") + "trailing",
#                     )
#                     app.logger.debug("Trailing Stop Data: %s", trailing_stop_data)

#                     trailing_stop_order = api.submit_order(
#                         order_data=trailing_stop_data
#                     )
#                     app.logger.debug("Trailing Stop Order: %s", trailing_stop_order)

#                     response_data = {
#                         "message": "Webhook received and processed successfully"
#                     }
#                     return jsonify(response_data), 200
#                 except Exception as e:
#                     app.logger.error("Error processing request: %s", str(e))
#                     error_message = {"error": "Failed to process webhook request"}
#                     return jsonify(error_message), 400
#             else:
#                 skip_message = {"Skip": "Skip webhook"}
#                 return jsonify(skip_message), 204

#         time.sleep(5)

