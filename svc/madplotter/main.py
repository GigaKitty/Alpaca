import alpaca_trade_api as tradeapi
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta

ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID", "your_api_key")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY", "your_secret_key")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv(
    "INFLUXDB_TOKEN",
    "some_token",
)

INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "influxox")


def fetch_historical_data(symbol, start_date, end_date, timeframe):
    api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url=ALPACA_BASE_URL)
    bars = api.get_bars(symbol, timeframe, start=start_date, end=end_date).df
    return bars


def save_to_influxdb(data, symbol):
    print(f"Connecting to InfluxDB at {INFLUXDB_URL}")
    try:
        with InfluxDBClient(
            url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
        ) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)

            for index, row in data.iterrows():
                point = (
                    Point("candle_data")
                    .tag("symbol", symbol)
                    .tag("timeframe", timeframe)
                    .field("vwap", row["vwap"])
                    .field("open", row["open"])
                    .field("high", row["high"])
                    .field("low", row["low"])
                    .field("close", row["close"])
                    .field("volume", row["volume"])
                    .time(index.isoformat())
                )

                print(point)
                write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
                print(f"Saved to InfluxDB: {index} - {symbol}")
    except Exception as e:
        print(f"Error connecting to InfluxDB: {e}")


if __name__ == "__main__":
    symbol = "SPY"
    start_date = (datetime.now() - timedelta(days=30)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )  # 1 year ago
    end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    timeframe = "1Min"

    historical_data = fetch_historical_data(symbol, start_date, end_date, timeframe)
    save_to_influxdb(historical_data, symbol)
