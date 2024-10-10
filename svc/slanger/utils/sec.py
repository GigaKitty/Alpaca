from flask import redirect, render_template, Flask, request, abort
import os
import ssl
import hmac
import hashlib


def validate_signature(data):
    """
    Validates a simple field value in the webhook to continue processing webhook otherwise fails.
    This isn't the most elegant solution but it adds some safety controls to arbitrary requests.
    Set the environment variable TRADINGVIEW_SECRET to the secret key from TradingView
    """
    signature = os.getenv("TRADINGVIEW_SECRET", False)
    
    if signature is False:
        #app.logger.error("TRADINGVIEW_SECRET environment variable not set")
        return render_template("404.html"), 404

    # Check if data is a dictionary
    if not isinstance(data, dict):
        #app.logger.error("Invalid data format: not a dictionary")
        return render_template("404.html"), 404

    # Check if data contains a "signature" key
    if "signature" not in data:
        #app.logger.error("Missing signature in data")
        return render_template("404.html"), 404

    provided_signature = data.get("signature")
    message = str(data).encode("utf-8")
    secret = signature.encode("utf-8")
    expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(provided_signature, expected_signature):
        #app.logger.error("Invalid signature")
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

    return True

def sanitize_data(data):
    sanitized = {}
    for key, value in data.items():
        if key.lower() in os.getenv("SENSITIVE_KEYS", "").split(","):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized

2
def authorize(data):
    #if validate_certificate() and validate_signature(data):
    if validate_signature(data):
        return True
    else:
        return False