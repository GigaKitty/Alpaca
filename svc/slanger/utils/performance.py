from flask import request, g
from functools import wraps
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime
import os
import time

environment = os.getenv("ENVIRONMENT", "dev")
bucket = f"slanger_performance_{environment}"
org = os.getenv("SLANGER_ORG", "org")
token = os.getenv("SLANGER_INFLUXDB_TOKEN")

url = "http://influxdb:8086"

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)


def timeit_ns(func):
    """
    - Decorator to measure the duration of a function
    - Write the duration to InfluxDB
    - Print the duration to the console
    - Return the result of the function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter_ns()
        result = func(*args, **kwargs)
        end_time = time.perf_counter_ns()
        #
        duration = end_time - start_time
        duration_ms = duration / 1_000_000  # Convert nanoseconds to milliseconds
        duration_s = duration / 1_000_000_000  # Convert nanoseconds to seconds

        if request.endpoint is None:
            request.endpoint = "unknown"
            
        point = (
            Point("performance")
            .tag("function", request.endpoint)  # Use request.endpoint as the function name
            .field("duration", duration)
            .field("duration_ms", duration_ms)
            .field("duration_s", duration_s)
            .time(datetime.datetime.now(datetime.timezone.utc), WritePrecision.NS)
        )
        write_api.write(bucket=bucket, org=org, record=point)
        print(
            f"{func.__name__} took {duration} ns or {duration_ms} ms or {duration_s} s"
        )
        return result

    return wrapper
