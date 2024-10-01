# post a buy or sell order based on the TradingView webhook data for kraken
from flask import Blueprint, jsonify, g

import requests
import time
import hashlib
import hmac
import base64
import urllib.parse
import os
kraken_market = Blueprint('kraken_market', __name__)

KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET")

def kraken_request(uri_path, data, KRAKEN_API_KEY, KRAKEN_API_SECRET):
	url = "https://api.kraken.com" + uri_path

	data["nonce"] = str(int(time.time() * 1000))
	post_data = urllib.parse.urlencode(data)
	message = uri_path.encode() + hashlib.sha256(data["nonce"].encode() + post_data.encode()).digest()
	signature = hmac.new(base64.b64decode(KRAKEN_API_SECRET), message, hashlib.sha512)
	sig_digest = base64.b64encode(signature.digest())

	headers = {
		"API-Key": os.getenv("KRAKEN_API_KEY"),
		"API-Sign": sig_digest.decode()
	}

	response = requests.post(url, headers=headers, data=data)
	return response.json()


@kraken_market.route("/market", methods=["POST"])
def order():
	if request.method == 'POST':
		data = request.json
		action = data.get('action')
		symbol = data.get('symbol')
		volume = data.get('volume', 1)
		price = data.get('price') 
		if not price:
			return jsonify({"status": "failure", "message": "Price is required"}), 400

		if action == 'buy':
			# Place a buy order
			try:
				order = kraken_request('/0/private/AddOrder', {
					'pair': symbol,
					'type': 'buy',
					'ordertype': 'limit',
					'price': price,
					'volume': 0.0075
				}, KRAKEN_API_KEY, KRAKEN_API_SECRET)
				print(f"Buy order placed: {order}")
				return jsonify({"status": "success", "order": order}), 200
			except Exception as e:
				print(f"Error placing buy order: {e}")
				return jsonify({"status": "failure", "message": str(e)}), 400

		elif action == 'sell':
			# Place a sell order
			try:
				order = kraken_request('/0/private/AddOrder', {
					'pair': symbol,
					'type': 'sell',
					'ordertype': 'limit',
					'price': price,
					'volume': 0.0075
				}, KRAKEN_API_KEY, KRAKEN_API_SECRET)
				print(f"Sell order placed: {order}")
				return jsonify({"status": "success", "order": order}), 200
			except Exception as e:
				print(f"Error placing sell order: {e}")
				return jsonify({"status": "failure", "message": str(e)}), 400

		else:
			return jsonify({"status": "failure", "message": "Invalid action"}), 400
	else:
		return jsonify({"status": "failure", "message": "Invalid request method"}), 400