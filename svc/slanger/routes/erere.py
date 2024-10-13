from flask import Flask, render_template
from utils.performance import timeit_ns
from config import app

@app.route("/erere", methods=["GET"])
@timeit_ns
def erere():
    # This route is automatically handled by PrometheusMetrics
    pass
