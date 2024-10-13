from flask import Flask, render_template
from utils.performance import timeit_ns
from config import app


@app.route("/health", methods=["GET"])
@timeit_ns
def health_check():
    return render_template("health.html"), 200
