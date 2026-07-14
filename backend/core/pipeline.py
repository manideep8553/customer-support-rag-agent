import logging
from typing import Generic, Protocol, TypeVar

logger = logging.getLogger("gigacorp.pipeline")

T = TypeVar("T")


class Stage(Protocol, Generic[T]):
    def __call__(self, data: T, context: dict | None = None) -> T: ...


class AsyncStage(Protocol, Generic[T]):
    async def __call__(self, data: T, context: dict | None = None) -> T: ...


class Pipeline(Generic[T]):
    def __init__(self, name: str = "unnamed"):
        self.name = name
        self._stages: list[tuple[str, Stage]] = []

    def add(self, name: str, stage: Stage) -> "Pipeline":
        self._stages.append((name, stage))
        return self

    def insert_before(self, target: str, name: str, stage: Stage) -> "Pipeline":
        idx = self._find_index(target)
        self._stages.insert(idx, (name, stage))
        return self

    def insert_after(self, target: str, name: str, stage: Stage) -> "Pipeline":
        idx = self._find_index(target)
        self._stages.insert(idx + 1, (name, stage))
        return self

    def remove(self, name: str) -> "Pipeline":
        self._stages = [(n, s) for n, s in self._stages if n != name]
        return self

    def replace(self, name: str, stage: Stage) -> "Pipeline":
        for i, (n, s) in enumerate(self._stages):
            if n == name:
                self._stages[i] = (name, stage)
                break
        return self

    def run(self, data: T, context: dict | None = None) -> T:
        ctx = context or {}
        for name, stage in self._stages:
            logger.debug("Pipeline %s: running stage %s", self.name, name)
            try:
                data = stage(data, ctx)
            except Exception:
                logger.exception("Pipeline %s stage %s failed", self.name, name)
                raise
        return data

    async def run_async(self, data: T, context: dict | None = None) -> T:
        ctx = context or {}
        for name, stage in self._stages:
            logger.debug("Pipeline %s: running stage %s", self.name, name)
            try:
                result = stage(data, ctx)
                if hasattr(result, "__await__"):
                    data = await result
                else:
                    data = result
            except Exception:
                logger.exception("Pipeline %s stage %s failed", self.name, name)
                raise
        return data

    @property
    def stage_names(self) -> list[str]:
        return [n for n, _ in self._stages]

    def _find_index(self, name: str) -> int:
        for i, (n, _) in enumerate(self._stages):
            if n == name:
                return i
        raise ValueError(f"Stage '{name}' not found in pipeline '{self.name}'")
