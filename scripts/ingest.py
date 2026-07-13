#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.di.container import container


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        result = container.kb_manager.ingest_file(file_path)
        print(f"Status: {result['status']}")
        print(f"Chunks ingested: {result['chunks_ingested']}")
        print(f"Message: {result['message']}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
