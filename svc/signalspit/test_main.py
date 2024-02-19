import unittest
from main import app


class TestNotionalEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_notional_success(self):
        response = self.app.post(
            "/notional", json={"ticker": "AAPL", "notional": 1000, "action": "buy"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["message"], "Webhook received and processed successfully"
        )

    def test_notional_invalid_data(self):
        response = self.app.post(
            "/notional", json={"ticker": "AAPL", "notional": "invalid", "action": "buy"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, b"Not Found")

    def test_notional_missing_data(self):
        response = self.app.post("/notional", json={"ticker": "AAPL", "action": "buy"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, b"Not Found")


if __name__ == "__main__":
    unittest.main()
