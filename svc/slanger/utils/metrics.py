from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge

metrics = PrometheusMetrics(app)

# Define a custom counter metric
post_requests_counter = metrics.counter(
    "post_requests",
    "Number of POST requests",
    labels={"endpoint": lambda: request.endpoint},
)

post_data_counter = Counter(
    "post_data_counter", "Counter for specific data in POST requests", ["data"]
)

# Define a custom gauge metric
post_data_gauge = Gauge(
    "post_data_gauge", "Gauge for specific data in POST requests", ["data"]
)
