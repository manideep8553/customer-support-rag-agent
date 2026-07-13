import re
from pathlib import Path

from backend.ports.document_loader import DocumentLoader, DocumentChunk
from backend.config import settings


class MarkdownLoader(DocumentLoader):
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def load(self, path: str) -> list[DocumentChunk]:
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {path}")
        text = filepath.read_text(encoding="utf-8")
        source = filepath.name
        return self.chunk(text, source=source)

    def chunk(self, text: str, source: str = "knowledge_base") -> list[DocumentChunk]:
        sections = self._split_by_headings(text)
        chunks = []
        for heading, content in sections:
            section_text = f"{heading}\n{content}".strip()
            sub_chunks = self._sub_chunk(section_text)
            for i, sc in enumerate(sub_chunks):
                chunks.append(DocumentChunk(
                    content=sc,
                    metadata={"source": source, "heading": heading.strip("# ").strip(), "chunk_index": i},
                ))
        return chunks

    def _split_by_headings(self, text: str) -> list[tuple[str, str]]:
        pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        if not matches:
            return [("", text)]
        sections = []
        for i, m in enumerate(matches):
            heading = m.group(0)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append((heading, content))
        return sections

    def _sub_chunk(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            newline_pos = text.rfind("\n", start, end)
            space_pos = text.rfind(" ", start, end)
            split_at = newline_pos if newline_pos > start else (space_pos if space_pos > start else end)
            chunks.append(text[start:split_at])
            start = split_at - self.chunk_overlap
        return chunks
