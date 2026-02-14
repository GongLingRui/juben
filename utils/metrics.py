"""Prometheus metrics helpers"""
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "juben_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "juben_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)
