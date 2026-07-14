import logging
from typing import Optional, Callable, Awaitable
from datetime import timedelta

from backend.config import settings

logger = logging.getLogger("gigacorp.background")


class BackgroundJobService:
    def __init__(self):
        self._redis_url = settings.job_queue_url
        self._concurrency = settings.job_concurrency
        self._redis_pool = None

    async def initialize(self):
        try:
            import redis.asyncio as aioredis
            self._redis_pool = aioredis.from_url(self._redis_url)
            logger.info("Background job service initialized (redis: %s)", self._redis_url)
        except Exception as e:
            logger.warning("Failed to initialize background job service: %s", e)

    async def close(self):
        if self._redis_pool:
            await self._redis_pool.close()
            self._redis_pool = None

    async def enqueue(
        self,
        job_name: str,
        *args,
        _defer_seconds: int = 0,
        **kwargs,
    ) -> Optional[str]:
        try:
            from arq.connections import create_pool
            pool = await create_pool(redis_settings=self._redis_url)

            job = await pool.enqueue_job(
                job_name,
                *args,
                _defer_seconds=_defer_seconds,
                **kwargs,
            )
            await pool.close()
            job_id = job.job_id if job else None
            logger.info("Enqueued job %s (id=%s)", job_name, job_id)
            return job_id
        except Exception as e:
            logger.warning("Failed to enqueue job %s: %s", job_name, e)
            return None

    async def enqueue_in(
        self,
        job_name: str,
        delay_seconds: int,
        *args,
        **kwargs,
    ) -> Optional[str]:
        return await self.enqueue(job_name, *args, _defer_seconds=delay_seconds, **kwargs)


_background_service: Optional[BackgroundJobService] = None


def get_background_service() -> BackgroundJobService:
    global _background_service
    if _background_service is None:
        _background_service = BackgroundJobService()
    return _background_service
