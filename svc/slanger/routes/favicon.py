from flask import Flask, render_template, send_from_directory
from utils.performance import timeit_ns
from config import app


@app.route("/favicon.ico", methods=["GET"])
@timeit_ns
def favicon():
    return send_from_directory(
        app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )
