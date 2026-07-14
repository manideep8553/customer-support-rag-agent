import sys
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.enterprise.logging_setup import setup_logging

setup_logging()

import logging
from backend.di.container import container
from backend.api.routes import build_router
from backend.auth.router import router as auth_router
from backend.customer.router import build_customer_router
from backend.customer.service import CustomerService
from backend.auth.database import async_session_factory
from backend.admin.router import build_admin_router
from backend.core.events import event_bus
from backend.core.registry import registry
from backend.errors import (
    ConfigurationError, GigaCorpError, friendly_error, log_exception,
)
from backend.deploy.config import get_profile, configure_from_profile
from backend.models.schemas import ErrorDetail
from backend.enterprise.routes import build_enterprise_router
from backend.enterprise.websocket.routes import build_ws_router
from backend.enterprise.middleware import CorrelationIDMiddleware, AuditMiddleware, MetricsEndpointMiddleware

logger = logging.getLogger("gigacorp")


def _setup_event_handlers():
    from backend.core.events import Event

    def log_all_events(event: Event):
        logger.debug("Event: %s | %s", event.name, event.data)

    event_bus.subscribe("query.completed", log_all_events)
    event_bus.subscribe("document.ingested", log_all_events)
    event_bus.subscribe("feedback.submitted", log_all_events)
    event_bus.subscribe("escalation.requested", log_all_events)

    logger.info("Event handlers registered")


async def _init_enterprise_services():
    try:
        if settings.cache_enabled:
            from backend.enterprise.cache_provider.redis_cache import get_cache
            cache = await get_cache()
            await cache.initialize()
            logger.info("Redis cache initialized")
    except Exception as e:
        logger.warning("Redis cache initialization failed: %s", e)

    try:
        from backend.enterprise.background.service import get_background_service
        bg = get_background_service()
        await bg.initialize()
    except Exception as e:
        logger.warning("Background job service initialization failed: %s", e)


async def _close_enterprise_services():
    try:
        if settings.cache_enabled:
            from backend.enterprise.cache_provider.redis_cache import get_cache
            cache = await get_cache()
            await cache.close()
    except Exception:
        pass

    try:
        from backend.enterprise.background.service import get_background_service
        bg = get_background_service()
        await bg.close()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version} [{settings.environment}]")
    logger.info("=" * 60)

    _setup_event_handlers()

    try:
        from backend.auth.database import init_db
        await init_db()
        logger.info("Database initialized")

        try:
            from backend.customer.seed import seed_customer_data
            async with async_session_factory() as seed_session:
                try:
                    await seed_customer_data(seed_session)
                except Exception as e:
                    logger.warning("Customer seed failed: %s", e)
                finally:
                    await seed_session.close()
        except Exception as e:
            log_exception(e, "lifespan.customer_seed")
            logger.warning("Customer seeding skipped: %s", e)
    except Exception as e:
        log_exception(e, "lifespan.database")
        logger.warning("Database init failed (will retry on first request): %s", e)

    try:
        container.preload()
    except Exception as e:
        log_exception(e, "lifespan.preload")
        logger.warning("Container preload failed: %s", e)

    try:
        kb_status = container.kb_manager.status()
        if not kb_status.get("initialized", False):
            logger.info("Knowledge base not initialized — ingesting default documents...")
            try:
                result = container.kb_manager.ingest_file()
                logger.info("  -> %s", result.get("message", "Ingestion completed"))
            except FileNotFoundError:
                logger.warning("No knowledge base documents found.")
            except Exception as e:
                logger.error("  -> Ingestion failed: %s", e)
        else:
            logger.info("Knowledge base loaded: %s chunks", kb_status.get("chunk_count", 0))
    except Exception as e:
        log_exception(e, "lifespan.startup")
        logger.warning("Knowledge base init failed, continuing: %s", e)

    await _init_enterprise_services()

    logger.info("Registered components: %s", registry.list())

    yield

    await _close_enterprise_services()

    try:
        from backend.auth.database import close_db
        await close_db()
    except Exception as e:
        logger.warning("Database shutdown error: %s", e)
    logger.info("Shutting down GigaCorp...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Customer Support RAG Platform with AI Orchestration",
    lifespan=lifespan,
)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorDetail(
            detail="; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()),
            code="VALIDATION_ERROR",
        ).model_dump(),
    )


@app.exception_handler(GigaCorpError)
async def gigacorp_error_handler(request: Request, exc: GigaCorpError):
    log_exception(exc, "GigaCorpError")
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(
            detail=friendly_error(exc),
            code=exc.code,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=ErrorDetail(
            detail="An unexpected error occurred. Please try again.",
            code="INTERNAL_ERROR",
        ).model_dump(mode="json"),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(MetricsEndpointMiddleware)


customer_service = CustomerService(lambda: async_session_factory())
router = build_router(container.orchestrator, container.kb_manager, customer_service=customer_service)
customer_router = build_customer_router(customer_service)
admin_router = build_admin_router(
    customer_service=customer_service,
    kb_manager=container.kb_manager,
    orchestrator=container.orchestrator,
    memory=container.memory,
    vector_store=container.vector_store,
)
enterprise_router = build_enterprise_router()
ws_router = build_ws_router()

app.include_router(auth_router)
app.include_router(router, prefix="/api/v1")
app.include_router(customer_router)
app.include_router(admin_router)
app.include_router(enterprise_router)
app.include_router(ws_router)

# Health endpoint at root
@app.get("/health")
async def root_health():
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

frontend_paths = [
    Path(__file__).resolve().parent.parent / "react-frontend" / "dist",
    Path(__file__).resolve().parent.parent / "frontend",
]
for fp in frontend_paths:
    if fp.exists():
        app.mount("/", StaticFiles(directory=str(fp), html=True), name="frontend")
        break

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
