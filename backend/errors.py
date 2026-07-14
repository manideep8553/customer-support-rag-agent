import time
import logging
import functools
import traceback
from typing import TypeVar, Callable, Any

logger = logging.getLogger("gigacorp.errors")

F = TypeVar("F", bound=Callable[..., Any])


class GigaCorpError(Exception):
    """Base exception for all GigaCorp application errors."""
    def __init__(self, message: str, *, code: str = "INTERNAL_ERROR", cause: Exception | None = None):
        self.code = code
        self.cause = cause
        super().__init__(message)


class EmbeddingError(GigaCorpError):
    """Raised when embedding generation fails."""
    def __init__(self, message: str = "Embedding generation failed", *, cause: Exception | None = None):
        super().__init__(message, code="EMBEDDING_ERROR", cause=cause)


class VectorStoreError(GigaCorpError):
    """Raised when vector store operations fail."""
    def __init__(self, message: str = "Vector store operation failed", *, cause: Exception | None = None):
        super().__init__(message, code="VECTOR_STORE_ERROR", cause=cause)


class LLMError(GigaCorpError):
    """Raised when LLM API calls fail."""
    def __init__(self, message: str = "LLM API call failed", *, cause: Exception | None = None):
        super().__init__(message, code="LLM_ERROR", cause=cause)


class DocumentLoadError(GigaCorpError):
    """Raised when document loading or chunking fails."""
    def __init__(self, message: str = "Document loading failed", *, cause: Exception | None = None):
        super().__init__(message, code="DOCUMENT_LOAD_ERROR", cause=cause)


class RetrievalError(GigaCorpError):
    """Raised when document retrieval fails."""
    def __init__(self, message: str = "Document retrieval failed", *, cause: Exception | None = None):
        super().__init__(message, code="RETRIEVAL_ERROR", cause=cause)


class MemoryError(GigaCorpError):
    """Raised when memory/session operations fail."""
    def __init__(self, message: str = "Memory operation failed", *, cause: Exception | None = None):
        super().__init__(message, code="MEMORY_ERROR", cause=cause)


class ConfigurationError(GigaCorpError):
    """Raised when component initialization fails due to configuration."""
    def __init__(self, message: str = "Component configuration failed", *, cause: Exception | None = None):
        super().__init__(message, code="CONFIGURATION_ERROR", cause=cause)


def log_exception(exc: Exception, context: str = "") -> None:
    """Log a detailed exception with traceback for debugging."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Exception in %s: %s\n%s", context, exc, tb)


def friendly_error(exc: Exception, default: str = "An unexpected error occurred. Please try again.") -> str:
    """Convert an exception to a user-friendly error message."""
    if isinstance(exc, EmbeddingError):
        return "I'm having trouble processing your request right now. Please try again in a moment."
    if isinstance(exc, VectorStoreError):
        return "Our knowledge base is temporarily unavailable. Please try again shortly."
    if isinstance(exc, LLMError):
        return "I'm unable to generate a response at the moment. Please try again later."
    if isinstance(exc, DocumentLoadError):
        return "There was a problem reading the document. Please check the file and try again."
    if isinstance(exc, RetrievalError):
        return "I had trouble searching for information. Please rephrase your question and try again."
    if isinstance(exc, MemoryError):
        return "There was a problem with your conversation. Please start a new chat."
    if isinstance(exc, ConfigurationError):
        return "The system is not fully configured. Please contact support."
    return default


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    default_return: Any = None,
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable[[F], F]:
    """Decorator that retries a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default 3).
        delay: Initial delay in seconds between retries (default 1.0).
        backoff: Multiplier for delay after each retry (default 2.0).
        exceptions: Tuple of exception types to catch (default Exception).
        default_return: Value to return if all attempts fail.
        on_retry: Optional callback(retry_exception, attempt_number).
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc = None
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        if on_retry:
                            on_retry(e, attempt)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs...",
                            func.__name__, attempt, max_attempts, e, current_delay,
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, e,
                        )
            if default_return is not None:
                return default_return
            if last_exc:
                raise last_exc
            return None
        return wrapper  # type: ignore
    return decorator
