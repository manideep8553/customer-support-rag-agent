import re
from backend.ingestion.pipeline import Document


class ContentSanitizer:
    CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    ZERO_WIDTH_CHARS_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')

    def __call__(self, doc: Document, context: dict | None = None) -> Document:
        text = doc.content
        text = self.CONTROL_CHARS_RE.sub("", text)
        text = self.ZERO_WIDTH_CHARS_RE.sub("", text)
        doc.content = text
        return doc


class LanguageFilter:
    ALLOWED_SCRIPTS_RE = re.compile(
        r'[\u0000-\u007F\u0080-\u024F\u0370-\u03FF\u0400-\u04FF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7AF]+'
    )

    def __init__(self, max_invalid_ratio: float = 0.3):
        self.max_invalid_ratio = max_invalid_ratio

    def __call__(self, doc: Document, context: dict | None = None) -> Document:
        valid_chars = len(self.ALLOWED_SCRIPTS_RE.findall(doc.content))
        total_chars = len(doc.content)
        if total_chars > 0 and valid_chars / total_chars < (1 - self.max_invalid_ratio):
            doc.metadata["flags"] = doc.metadata.get("flags", []) + ["high_garbage_ratio"]
        return doc
