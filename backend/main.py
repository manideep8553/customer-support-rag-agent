import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.di.container import container
from backend.api.routes import build_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-6s | %(message)s",
)
logger = logging.getLogger("gigacorp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)

    kb_status = container.kb_manager.status()
    if not kb_status["initialized"]:
        logger.info("Knowledge base not initialized — ingesting default documents...")
        try:
            result = container.kb_manager.ingest_file()
            logger.info(f"  -> {result['message']}")
        except FileNotFoundError:
            logger.warning("  -> No knowledge base documents found. Place .md files in data/knowledge_base/")
        except Exception as e:
            logger.error(f"  -> Ingestion failed: {e}")
    else:
        logger.info(f"Knowledge base loaded: {kb_status['chunk_count']} chunks")

    yield

    logger.info("Shutting down GigaCorp RAG Agent...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modular Customer Support RAG Agent with LangGraph Orchestration",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = build_router(container.orchestrator, container.kb_manager)
app.include_router(router, prefix="/api/v1")

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
