import asyncio
import json
import os
import redis
import logging

# import requests
import redis.asyncio as aioredis
import requests
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
write_api = influxdb_client.write_api(write_options=ASYNCHRONOUS)


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


async def process_and_store_data(data):
    """
    Process the WebSocket data and store it in InfluxDB.
    """
    try:
        data_json = json.loads(data)

        # Check if data_json is a list
        if isinstance(data_json, list):
            for item in data_json:
                await store_data_point(item)
        else:
            await store_data_point(data_json)

    except json.JSONDecodeError:
        logging.error("Invalid JSON received in the WebSocket message.")


async def store_data_point(data_point):
    """
    Store a single data point in InfluxDB.
    """
    ticker = data_point.get("S")
    price = data_point.get("p")
    timestamp = data_point.get("t")
    tickerid = data_point.get("i")
    exchange = data_point.get("x")
    size = data_point.get("s")
    tape = data_point.get("z")

    if ticker and price and timestamp:
        point = (
            Point("stock_data")
            .tag("ticker", ticker)
            .field("trade_id", tickerid)
            .field("exchange", exchange)
            .field("size", size)
            .field("tape", tape)
            .field("exchange", exchange)
            .field("price", price)
            .time(timestamp, WritePrecision.NS)
        )
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"Data point: {data_point}")
        logging.info(f"Data written to InfluxDB: {data_point}")


async def redis_listener():
    pubsub = redis.pubsub()
    await pubsub.subscribe("stocks_channel")

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

#@TODO: add crypto support data otherwise except for performance this is done.