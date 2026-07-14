import re
from backend.ingestion.pipeline import Document


class TextNormalizer:
    def __call__(self, doc: Document, context: dict | None = None) -> Document:
        text = doc.content
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\n{4,}", "\n\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        doc.content = text.strip()
        return doc


class MetadataEnricher:
    HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)

    def __call__(self, doc: Document, context: dict | None = None) -> Document:
        if not doc.metadata.get("title"):
            match = self.HEADING_RE.search(doc.content)
            if match:
                doc.metadata["title"] = match.group(1).strip()
        doc.metadata["char_count"] = len(doc.content)
        doc.metadata["word_count"] = len(doc.content.split())
        return doc


class TextChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    HEADING_RE = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)

    def __call__(self, doc: Document, context: dict | None = None) -> list[Document]:
        chunks = self._split_by_headings(doc)
        return self._enforce_size_limit(chunks)

    def _split_by_headings(self, doc: Document) -> list[Document]:
        parts = self.HEADING_RE.split(doc.content)
        sections = []
        current_section = ""
        current_heading = ""
        for part in parts:
            if re.match(r"^#{1,3}\s+", part):
                if current_section:
                    sections.append((current_heading, current_section.strip()))
                current_heading = part.strip()
                current_section = part + "\n"
            else:
                current_section += part
        if current_section.strip():
            sections.append((current_heading, current_section.strip()))

        result = []
        for heading, text in sections:
            if len(text) <= 20:
                continue
            chunk_docs = self._chunk_section(doc, heading, text)
            result.extend(chunk_docs)
        return result

    def _chunk_section(self, doc: Document, heading: str, text: str) -> list[Document]:
        if len(text) <= self.chunk_size:
            meta = dict(doc.metadata)
            meta["heading"] = heading.lstrip("#").strip() if heading else ""
            return [Document(content=text, metadata=meta, source=doc.source, path=doc.path)]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunk_text = text[start:]
                meta = dict(doc.metadata)
                meta["heading"] = heading.lstrip("#").strip() if heading else ""
                chunks.append(Document(content=chunk_text, metadata=meta, source=doc.source, path=doc.path))
                break

            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start + self.chunk_size // 2:
                end = newline_pos
            else:
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + self.chunk_size // 2:
                    end = space_pos

            chunk_text = text[start:end].strip()
            if chunk_text:
                meta = dict(doc.metadata)
                meta["heading"] = heading.lstrip("#").strip() if heading else ""
                chunks.append(Document(content=chunk_text, metadata=meta, source=doc.source, path=doc.path))
            start = end - self.chunk_overlap

        return chunks

    def _enforce_size_limit(self, chunks: list[Document]) -> list[Document]:
        return [c for c in chunks if len(c.content) > 0]
