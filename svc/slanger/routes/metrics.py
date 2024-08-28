from config import app

@app.route("/metrics")
def metrics_endpoint():
    return "Metrics are exposed!"
