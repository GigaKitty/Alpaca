import asyncio
import json
import os
import redis
import logging
import datetime
import numpy as np  # Import numpy

# import requests
import redis.asyncio as aioredis
import pymarketstore as pymkts
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

# InfluxDB configuration
INFLUXDB_URL = "http://influxdb:8086"
INFLUXDB_TOKEN = os.getenv(
    "INFLUXDB_TOKEN",
)
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "influxox")
# Initialize InfluxDB client with batch write options
influxdb_client = InfluxDBClient(
    url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
)
timeframe = "1Min"
attribute_group = "OHLCV"

REQUIRED_BAR_FIELDS = {"t", "o", "h", "l", "c", "v"}

write_api = influxdb_client.write_api(write_options=ASYNCHRONOUS)
marketstore_client = pymkts.Client(f"http://marketstore:5993/rpc")
r = redis.Redis(host="redis-stack-core", port=6379)
redis_host = os.getenv("REDIS_HOST", "redis-stack")
redis_port = 6379
redis = aioredis.Redis(
    host=redis_host,
    port=redis_port,
    socket_timeout=10,  # Increase the timeout value
    connection_pool=aioredis.ConnectionPool(
        host="redis-stack", port=redis_port, max_connections=10
    ),
)


# @TODO: add other types like trades, quotes, etc.
def is_bar_data(data):
    """
    Check if the incoming data is bar data.
    """
    if data.get("T") in ["b", "d", "u"]:
        return True


def parse_datetime(dt_str):
    try:
        return datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    except ValueError as e:
        logging.error(f"Error parsing datetime: {e}")
        return None


async def process_and_store_data(data):
    """
    Process and store incoming data.
    """
    data = json.loads(data)
    if isinstance(data, list):
        for item in data:
            if is_bar_data(item):
                await store_influx_bars(item)
                await store_marketstore_bars(item)


async def store_marketstore_bars(data):
    """
    Store the data in Marketstore.
    """
    logging.info(f"Storing data in Marketstore: {data}")

    try:
        epoch_time = parse_datetime(data["t"])

        # @TODO: I'm not sure this whole datafram is necessary, but I'm keeping it for now.
        df = np.array(
            [
                (
                    epoch_time,
                    data.get("o", 0.0),
                    data.get("h", 0.0),
                    data.get("l", 0.0),
                    data.get("c", 0.0),
                    data.get("v", 0.0),
                )
            ],
            dtype=[
                ("Epoch", "i8"),  # int64
                ("Open", "f8"),  # float64
                ("High", "f8"),  # float64
                ("Low", "f8"),  # float64
                ("Close", "f8"),  # float64
                ("Volume", "f8"),  # float64
            ],
        )

        # Determine the symbol and timeframe
        symbol = data["S"].replace("/", "-")  # Replace '/' with '_' this is because the / is used as a delimiter in Marketstore
        # Write to Marketstore       
        marketstore_client.write(df, f"{symbol}/{timeframe}/{attribute_group}")
        
    except Exception as e:
        print(f"Error storing data: {e}")


async def store_influx_bars(data_point):
    """
    Store a single data point in InfluxDB.
    """
    point = (
        Point("bars")
        .tag("ticker", data_point.get("S"))
        .field("close", data_point.get("c"))
        .field("high", data_point.get("h"))
        .field("low", data_point.get("l"))
        .field("open", data_point.get("o"))
        .field("volume", data_point.get("v"))
        .field("price", data_point.get("p"))
        .time(data_point.get("t"), WritePrecision.NS)
    )
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
    logging.info(f"Data written to InfluxDB: {data_point}")


async def redis_listener():
    pubsub = redis.pubsub()
    await pubsub.subscribe("stocks_channel", "crypto_channel")

    async for message in pubsub.listen():
        if message["type"] == "message":
            await process_and_store_data(message["data"])


async def main():
    await redis_listener()


if __name__ == "__main__":
    """
    Entry point for the application
    """
    asyncio.run(main())

# @TODO: add crypto support data otherwise except for performance this is done.
