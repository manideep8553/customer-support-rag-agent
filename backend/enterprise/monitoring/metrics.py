import logging
import time
from functools import wraps
from typing import Optional

from backend.config import settings

logger = logging.getLogger("gigacorp.metrics")


class MetricsCollector:
    def __init__(self):
        self._enabled = settings.metrics_enabled
        self._metrics = {}

    def increment(self, metric_name: str, value: int = 1, tags: Optional[dict] = None):
        if not self._enabled:
            return
        key = self._make_key(metric_name, tags)
        self._metrics[key] = self._metrics.get(key, 0) + value

    def gauge(self, metric_name: str, value: float, tags: Optional[dict] = None):
        if not self._enabled:
            return
        key = self._make_key(metric_name, tags)
        self._metrics[key] = value

    def timing(self, metric_name: str, duration_ms: float, tags: Optional[dict] = None):
        if not self._enabled:
            return
        key = self._make_key(metric_name, tags)
        if key not in self._metrics:
            self._metrics[key] = {"count": 0, "total_ms": 0.0, "min": float("inf"), "max": 0.0}
        stats = self._metrics[key]
        stats["count"] += 1
        stats["total_ms"] += duration_ms
        stats["min"] = min(stats["min"], duration_ms)
        stats["max"] = max(stats["max"], duration_ms)
        stats["avg"] = stats["total_ms"] / stats["count"]

    def _make_key(self, name: str, tags: Optional[dict]) -> str:
        if tags:
            tag_str = "|".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}[{tag_str}]"
        return name

    def snapshot(self) -> dict:
        return dict(self._metrics)

    def clear(self):
        self._metrics.clear()

    def prometheus_metrics(self) -> str:
        lines = []
        for key, value in self._metrics.items():
            metric_name = key.split("[")[0].replace(".", "_")
            if isinstance(value, dict):
                for stat, stat_val in value.items():
                    lines.append(f"# HELP {metric_name}_{stat} {metric_name} {stat}")
                    lines.append(f"# TYPE {metric_name}_{stat} gauge")
                    lines.append(f"{metric_name}_{stat} {stat_val}")
            else:
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name} {value}")
        return "\n".join(lines)


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def track_time(metric_name: str, tags: Optional[dict] = None):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = (time.monotonic() - start) * 1000
                get_metrics_collector().timing(metric_name, elapsed, tags)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.monotonic() - start) * 1000
                get_metrics_collector().timing(metric_name, elapsed, tags)

        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
            return async_wrapper
        return sync_wrapper
    return decorator
