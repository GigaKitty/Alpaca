from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import TrailingStopOrderRequest
from config import api, app, POSTPROCESS
from flask import Flask, g, jsonify, make_response
from routes.equity.trailing_stop import trailing_stop
from routes.equity.trailing_stop_tiered import trailing_stop_tiered
from utils.performance import timeit_ns
import asyncio

@app.after_request
@timeit_ns
def after_request(response):
    if hasattr(g, "data"):
        postprocess_list = g.data.get("postprocess")
        if isinstance(postprocess_list, list) and any(
            item in POSTPROCESS for item in postprocess_list
        ):
            for func in postprocess_list:
                if func == "trailing_stop":
                    asyncio.run(trailing_stop(g.data, response))
                elif func == "trailing_stop_tiered":
                    asyncio.run(trailing_stop_tiered(g.data, response))


    response_data = {"message": "Webhook received and processed successfully"}
    return make_response(jsonify(response_data), 200)