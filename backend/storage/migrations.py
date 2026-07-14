import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("gigacorp.migrations")


class MigrationManager:
    def __init__(self):
        self._migrations: dict[str, Any] = {}

    def register(self, version: str, up: Callable, down: Optional[Callable] = None, description: str = "") -> None:
        self._migrations[version] = {"up": up, "down": down, "description": description}
        logger.info("Registered migration v%s: %s", version, description)

    async def run(self, target_version: str | None = None) -> list[str]:
        applied = []
        sorted_versions = sorted(self._migrations.keys())
        for version in sorted_versions:
            if target_version and version > target_version:
                break
            try:
                await self._migrations[version]["up"]()
                applied.append(version)
                logger.info("Applied migration v%s: %s", version, self._migrations[version]["description"])
            except Exception as e:
                logger.error("Migration v%s failed: %s", version, e)
                raise
        return applied

    async def rollback(self, target_version: str) -> list[str]:
        rolled_back = []
        sorted_versions = sorted(self._migrations.keys(), reverse=True)
        for version in sorted_versions:
            if version <= target_version:
                break
            down_fn = self._migrations[version].get("down")
            if down_fn:
                try:
                    await down_fn()
                    rolled_back.append(version)
                    logger.info("Rolled back migration v%s", version)
                except Exception as e:
                    logger.error("Rollback v%s failed: %s", version, e)
                    raise
        return rolled_back


migration_manager = MigrationManager()


def migration(version: str, description: str = ""):
    def decorator(func):
        migration_manager.register(version, func, description=description)
        return func
    return decorator
