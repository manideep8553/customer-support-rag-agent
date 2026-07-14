import logging
from datetime import datetime

logger = logging.getLogger("gigacorp.tasks")


async def send_email_task(ctx, to_email: str, subject: str, html_body: str):
    from backend.enterprise.email_service.service import get_email_service
    service = get_email_service()
    result = await service.send_email(to_email=to_email, subject=subject, html_body=html_body)
    logger.info("Email task completed: to=%s subject=%s success=%s", to_email, subject, result)
    return result


async def process_ingestion_task(ctx, file_path: str):
    from backend.di.container import container
    kb = container.kb_manager
    result = kb.ingest_file(file_path)
    logger.info("Ingestion task completed: file=%s result=%s", file_path, result)
    return result


async def cleanup_expired_sessions_task(ctx):
    from backend.di.container import container
    memory = container.memory
    purged = memory.cleanup_expired()
    logger.info("Session cleanup task completed: purged=%s", purged)
    return {"purged": purged}


async def generate_daily_report_task(ctx):
    logger.info("Daily report generation started: %s", datetime.utcnow().isoformat())
    return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}


class WorkerSettings:
    functions = [
        send_email_task,
        process_ingestion_task,
        cleanup_expired_sessions_task,
        generate_daily_report_task,
    ]
    redis_settings = None
