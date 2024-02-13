import os

from flask import redirect


# Validates the signature from TradingView
# @TODO: This should be updated to check SSL and/or IP so we can remove signature from the webhook
def validate_signature(data):
    """
    Validates a simple field value in the webhook to continue processing webhook otherwise fails.
    This isn't the most elegant solution but it adds some safety controls to arbitrary requests.
    We can further improve upon this by validating the request is legitimately coming from TradingView using SSL and/or at least IP
    Set the environment variable TRADINGVIEW_SECRET to the secret key from TradingView
    """
    signature = os.getenv("TRADINGVIEW_SECRET")

    if signature != data.get("signature"):
        return redirect("/404")  # Redirect to the 404 page
    else:
        return True
