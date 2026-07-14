import logging
import inspect
from typing import Callable, Any
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("gigacorp.events")


@dataclass
class Event:
    name: str
    data: dict = field(default_factory=dict)


EventHandler = Callable[[Event], Any]


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)
        logger.debug("Subscribed %s to %s", getattr(handler, "__name__", handler), event_name)

    def publish(self, event: Event) -> None:
        for handler in self._subscribers.get(event.name, []):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    logger.warning("Event handler %s is async but publish is sync — use publish_async", handler)
            except Exception as e:
                logger.exception("Event handler %s failed for event %s", handler, event.name)

    async def publish_async(self, event: Event) -> None:
        for handler in self._subscribers.get(event.name, []):
            try:
                result = handler(event)
                if inspect.iscoroutine(result):
                    await result
            except Exception as e:
                logger.exception("Event handler %s failed for async event %s", handler, event.name)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].remove(handler)


event_bus = EventBus()
