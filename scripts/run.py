#!/usr/bin/env python3
"""Script to run the GigaCorp Customer Support RAG Agent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

from backend.config import settings


def main():
    print("=" * 60)
    print(f"  {settings.app_name} v{settings.app_version}")
    print(f"  Listening on http://{settings.host}:{settings.port}")
    print(f"  API docs at http://{settings.host}:{settings.port}/docs")
    print("=" * 60)

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
