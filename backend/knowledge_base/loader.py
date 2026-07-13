import re
from pathlib import Path
from typing import Optional

from backend.config import settings


class DocumentLoader:
    def __init__(self):
        self.base_path = settings.knowledge_base_path

    def load_markdown(self, file_path: Optional[str] = None) -> str:
        if file_path:
            path = Path(file_path)
        else:
            md_files = list(self.base_path.glob("*.md"))
            if not md_files:
                raise FileNotFoundError(f"No markdown files found in {self.base_path}")
            path = md_files[0]

        return path.read_text(encoding="utf-8")

    def chunk_document(self, text: str) -> list[str]:
        sections = self._split_by_headings(text)
        chunks = []
        for section in sections:
            section_chunks = self._chunk_by_size(section)
            chunks.extend(section_chunks)
        return chunks

    def _split_by_headings(self, text: str) -> list[str]:
        heading_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
        parts = heading_pattern.split(text)

        sections = []
        current_section = ""
        for part in parts:
            if re.match(r"^#{1,3}\s+", part):
                if current_section:
                    sections.append(current_section.strip())
                current_section = part
            else:
                current_section += part

        if current_section.strip():
            sections.append(current_section.strip())

        return [s for s in sections if len(s) > 20]

    def _chunk_by_size(self, text: str) -> list[str]:
        if len(text) <= settings.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + settings.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break

            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start + settings.chunk_size // 2:
                end = newline_pos
            else:
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + settings.chunk_size // 2:
                    end = space_pos

            chunks.append(text[start:end].strip())
            start = end - settings.chunk_overlap

        return [c for c in chunks if c]
