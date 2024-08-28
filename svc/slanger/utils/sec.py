from flask import redirect, render_template, Flask, request, abort
import os
import ssl

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


def validate_certificate():
    # Verify the certificate
    if not request.is_secure:
        abort(403)  # Request is not over HTTPS

    cert = request.environ.get("SSL_CLIENT_CERT")
    if not cert:
        abort(403)  # No client certificate provided

    try:
        cert = ssl.PEM_cert_to_DER_cert(cert)
        x509 = ssl._ssl._test_decode_cert(cert)

        subject = dict(x509["subject"])
        san = dict(x509["subjectAltName"])

        # Check certificate fields
        if (
            subject.get("C") != "US"
            or subject.get("ST") != "Ohio"
            or subject.get("L") != "Westerville"
            or subject.get("O") != "TradingView, Inc."
            or subject.get("CN") != "TradingView Webhooks"
            or san.get("email") != "webhook-server@tradingview.com"
        ):
            abort(403)  # Certificate fields do not match

    except Exception as e:
        abort(403)  # Invalid certificate

    # Process the webhook payload
    data = request.json
    # Handle the webhook data as needed
    return "Webhook received", 200


def sanitize_data(data):
    sanitized = {}
    for key, value in data.items():
        if key.lower() in os.getenv("SENSITIVE_KEYS", "").split(","):
            sanitized[key] = '***REDACTED***'
        else:
            sanitized[key] = value
    return sanitized
