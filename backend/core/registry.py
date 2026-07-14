import logging
from typing import Any, TypeVar

logger = logging.getLogger("gigacorp.registry")

T = TypeVar("T")


class ComponentRegistry:
    def __init__(self):
        self._components: dict[str, Any] = {}
        self._factories: dict[str, callable] = {}
        self._aliases: dict[str, str] = {}

    def register(self, name: str, instance: Any, alias: str | None = None) -> None:
        self._components[name] = instance
        if alias:
            self._aliases[alias] = name
        logger.debug("Registered component: %s", name)

    def register_factory(self, name: str, factory: callable, alias: str | None = None) -> None:
        self._factories[name] = factory
        if alias:
            self._aliases[alias] = name
        logger.debug("Registered factory: %s", name)

    def get(self, name: str) -> Any:
        resolved = self._aliases.get(name, name)
        if resolved in self._factories:
            if resolved not in self._components:
                self._components[resolved] = self._factories[resolved]()
                logger.debug("Initialized lazy component: %s", resolved)
            return self._components[resolved]
        if resolved in self._components:
            return self._components[resolved]
        raise KeyError(f"Component '{name}' not found in registry")

    def has(self, name: str) -> bool:
        resolved = self._aliases.get(name, name)
        return resolved in self._components or resolved in self._factories

    def get_or_none(self, name: str) -> Any | None:
        try:
            return self.get(name)
        except KeyError:
            return None

    def list(self) -> list[str]:
        return list(self._components.keys()) + list(self._factories.keys())

    def clear(self) -> None:
        self._components.clear()
        self._factories.clear()
        self._aliases.clear()


registry = ComponentRegistry()
