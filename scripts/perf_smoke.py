"""简单性能基线测试（HTTP请求延迟）"""
import os
import time
import statistics
import httpx

BASE_URL = os.getenv("PERF_BASE_URL", "http://localhost:8000")
ENDPOINT = os.getenv("PERF_ENDPOINT", "/health")
REQUESTS = int(os.getenv("PERF_REQUESTS", "50"))


def main():
    url = f"{BASE_URL}{ENDPOINT}"
    latencies = []
    with httpx.Client(timeout=10.0) as client:
        for _ in range(REQUESTS):
            start = time.time()
            r = client.get(url)
            r.raise_for_status()
            latencies.append((time.time() - start) * 1000)

    p50 = statistics.median(latencies)
    p90 = statistics.quantiles(latencies, n=10)[8]
    p99 = statistics.quantiles(latencies, n=100)[98]
    avg = statistics.mean(latencies)

    print(f"Requests: {REQUESTS}")
    print(f"Avg: {avg:.2f}ms")
    print(f"P50: {p50:.2f}ms")
    print(f"P90: {p90:.2f}ms")
    print(f"P99: {p99:.2f}ms")


if __name__ == "__main__":
    main()
