import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from functools import wraps

bucket = "slanger_metrics"
org = "org"
token = "vqZtZlxR-jWDAbpZLjFv56ScejS9ARjtGSTGhnPjugIJ2Y1MBZ1d2S5YkkwRXr6Y38T28EL2oJLLSVhiu1wYGw=="
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

        point = Point("performance") \
            .tag("function", func.__name__) \
            .field("duration", duration)
        write_api.write(bucket=bucket, org=org, record=point)
        print(f"{func.__name__} took {duration} ns or {duration_ms} ms or {duration_s} s")
        return result
    return wrapper