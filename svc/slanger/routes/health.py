from flask import Flask, render_template

# Add app.route for health check
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return render_template("health.html"), 200
