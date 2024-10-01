import os
import redis
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

REDIS_STREAM = "stocks_channel"
REDIS_GROUP = "mygroup"
REDIS_CONSUMER = "myconsumer"

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "vqZtZlxR-jWDAbpZLjFv56ScejS9ARjtGSTGhnPjugIJ2Y1MBZ1d2S5YkkwRXr6Y38T28EL2oJLLSVhiu1wYGw=="
INFLUXDB_ORG = "org"
INFLUXDB_BUCKET = "my-bucket"


def subscribe_to_redis_stream():
    r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"))

    try:
        r.xgroup_create(REDIS_STREAM, REDIS_GROUP, id="0", mkstream=True)
        print(f"Created Redis group {REDIS_GROUP} for stream {REDIS_STREAM}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            print(f"Redis group {REDIS_GROUP} already exists")
        else:
            raise

    while True:
        try:
            messages = r.xreadgroup(
                REDIS_GROUP, REDIS_CONSUMER, {REDIS_STREAM: ">"}, count=1, block=5000
            )
            for message in messages:
                stream, message_data = message
                message_id, message_body = message_data[0]
                process_message(message_body)
                r.xack(REDIS_STREAM, REDIS_GROUP, message_id)
        except Exception as e:
            print(f"Error reading from Redis stream: {e}")


def process_message(message):
    with InfluxDBClient(
        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
    ) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = (
            Point("measurement_name")
            .tag("tag_key", "tag_value")
            .field("field_key", float(message[b"field_key"]))
        )
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"Published to InfluxDB: {message}")
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = (
            Point("measurement_name")
            .tag("tag_key", "tag_value")
            .field("field_key", float(message[b"field_key"]))
        )
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"Published to InfluxDB: {message}")


if __name__ == "__main__":
    subscribe_to_redis_stream()
