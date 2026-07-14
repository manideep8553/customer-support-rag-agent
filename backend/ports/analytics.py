from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class AnalyticsEvent:
    event_type: str
    session_id: str
    user_id: str | None = None
    properties: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AnalyticsProvider(Protocol):
    async def track(self, event: AnalyticsEvent) -> None: ...

    async def track_batch(self, events: list[AnalyticsEvent]) -> None: ...

    async def query(self, event_type: str, start: datetime, end: datetime) -> list[AnalyticsEvent]: ...

    async def get_metrics(self, metric_name: str, period: str = "day") -> dict: ...
