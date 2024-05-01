import os

from flask import redirect, render_template


# Validates the signature from TradingView
# @TODO: This should be updated to check SSL and/or IP so we can remove signature from the webhook
def validate_signature(data):
    """
    Validates a simple field value in the webhook to continue processing webhook otherwise fails.
    This isn't the most elegant solution but it adds some safety controls to arbitrary requests.
    We can further improve upon this by validating the request is legitimately coming from TradingView using SSL and/or at least IP
    Set the environment variable TRADINGVIEW_SECRET to the secret key from TradingView
    """
    signature = os.getenv("TRADINGVIEW_SECRET", False)

    if signature is False:
        return render_template("404.html"), 404

    # Check if data is a dictionary
    if not isinstance(data, dict):
        return render_template("404.html"), 404

    # Check if data contains a "signature" key
    if "signature" not in data:
        return render_template("404.html"), 404

    if signature != data.get("signature"):
        return render_template("404.html"), 404
    else:
        return True
