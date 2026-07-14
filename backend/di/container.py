import logging

from backend.config import settings
from backend.core.registry import registry
from backend.ports.vector_store import VectorStore
from backend.ports.memory import Memory
from backend.ports.document_loader import DocumentLoader
from backend.ports.llm import LLM
from backend.ports.embedding import EmbeddingModel

from backend.adapters.vector_store.faiss_adapter import FAISSAdapter
from backend.adapters.vector_store.chroma_adapter import ChromaDBAdapter
from backend.adapters.memory.langgraph_memory import LangGraphMemory
from backend.adapters.memory.json_file_memory import JsonFileMemory
from backend.adapters.chunking.langchain_splitter import LangChainMarkdownLoader

from backend.knowledge_base.store import KnowledgeBaseManager
from backend.orchestration.graph import SupportGraph
from backend.errors import ConfigurationError, log_exception

logger = logging.getLogger("gigacorp.di")


_EXTENSION_HOOKS = []


def on_container_init(hook):
    _EXTENSION_HOOKS.append(hook)
    return hook


class Container:
    def __init__(self):
        self._init_all()

    def _init_all(self):
        self._init_embedding()
        self._init_vector_store()
        self._init_doc_loader()
        self._init_memory()
        self._init_llm()
        self._init_kb_manager()
        self._init_orchestrator()
        self._run_extension_hooks()
        self._log_summary()

    def _run_extension_hooks(self):
        for hook in _EXTENSION_HOOKS:
            try:
                hook(self)
            except Exception as e:
                logger.warning("Extension hook %s failed: %s", getattr(hook, "__name__", hook), e)

    def _log_summary(self):
        llm_status = f"{settings.llm_provider or 'rule-based'}" if self.llm else "rule-based"
        logger.info(
            "Container initialized | Registry: %d components | Embedding: %s/%s | Vector: %s | Memory: %s | LLM: %s",
            len(registry.list()),
            settings.embedding_provider, settings.embedding_model,
            settings.vector_store_type,
            settings.memory_backend,
            llm_status,
        )

    def _init_embedding(self):
        provider = settings.embedding_provider
        model = settings.embedding_model
        logger.info("Initializing embedding model: %s (%s)", provider, model)
        try:
            if provider == "openai":
                from backend.adapters.embeddings.openai_embedding import OpenAIEmbedding
                instance = OpenAIEmbedding(model_name=model, api_key=settings.openai_api_key)
            elif provider == "huggingface":
                from backend.adapters.embeddings.hf_embedding import HFEmbedding
                instance = HFEmbedding(model_name=model)
            else:
                raise ConfigurationError(f"Unknown embedding provider: {provider}")
            registry.register("embedding_model", instance)
        except Exception as e:
            log_exception(e, "Container.embedding")
            logger.critical("Failed to initialize embedding model.")
            raise

    def _init_vector_store(self):
        vs_type = settings.vector_store_type
        logger.info("Initializing vector store: %s", vs_type)
        try:
            if vs_type == "chromadb":
                instance = ChromaDBAdapter(embedding_model=self.embedding_model)
            elif vs_type == "faiss":
                instance = FAISSAdapter(embedding_model=self.embedding_model)
            else:
                raise ConfigurationError(f"Unknown vector store type: {vs_type}")
            registry.register("vector_store", instance)
        except Exception as e:
            log_exception(e, "Container.vector_store")
            logger.critical("Failed to initialize vector store.")
            raise

    def _init_memory(self):
        backend = settings.memory_backend
        logger.info("Initializing memory backend: %s", backend)
        try:
            if backend == "json_file":
                instance = JsonFileMemory()
            else:
                instance = LangGraphMemory()
            registry.register("memory", instance)
        except Exception as e:
            logger.error("Failed to initialize %s memory, falling back to LangGraphMemory: %s", backend, e)
            registry.register("memory", LangGraphMemory())

    def _init_doc_loader(self):
        registry.register("doc_loader", LangChainMarkdownLoader())

    def _init_llm(self):
        provider = settings.llm_provider
        if not provider:
            logger.info("No LLM provider configured — using rule-based answers")
            registry.register("llm", None)
            return
        logger.info("Initializing LLM provider: %s", provider)
        try:
            if provider == "openai":
                if not settings.openai_api_key:
                    logger.warning("OpenAI provider selected but no API key configured. Falling back to rule-based.")
                    registry.register("llm", None)
                    return
                from backend.adapters.llm.openai_adapter import OpenAIAdapter
                instance = OpenAIAdapter(model=settings.llm_model or "gpt-4o-mini")
            elif provider == "ollama":
                from backend.adapters.llm.ollama_adapter import OllamaAdapter
                instance = OllamaAdapter(model=settings.llm_model or "llama3.1:8b")
            else:
                logger.warning("Unknown LLM provider: %s", provider)
                registry.register("llm", None)
                return
            registry.register("llm", instance)
        except Exception as e:
            logger.error("Failed to initialize LLM provider %s: %s. Falling back to rule-based.", provider, e)
            registry.register("llm", None)

    def _init_kb_manager(self):
        instance = KnowledgeBaseManager(vector_store=self.vector_store, doc_loader=self.doc_loader)
        registry.register("kb_manager", instance)

    def _init_orchestrator(self):
        try:
            instance = SupportGraph(
                vector_store=self.vector_store,
                memory_backend=self.memory,
                llm=self.llm,
            )
            registry.register("orchestrator", instance)
        except Exception as e:
            log_exception(e, "Container.orchestrator")
            logger.critical("Failed to initialize orchestrator.")
            raise

    def preload(self):
        logger.info("Preloading components...")
        if self.embedding_model:
            try:
                self.embedding_model.embed(["warmup"])
                logger.info("Embedding model warmed up")
            except Exception as e:
                logger.warning("Embedding model warmup failed: %s", e)
        if self.vector_store:
            try:
                if self.vector_store.is_initialized:
                    logger.info("Vector store is loaded (%d chunks)", self.vector_store.chunk_count)
            except Exception as e:
                logger.warning("Vector store status check failed: %s", e)
        logger.info("Preloading complete")

    def register(self, name: str, instance, alias: str | None = None):
        registry.register(name, instance, alias)

    def get(self, name: str):
        return registry.get(name)

    def get_or_none(self, name: str):
        return registry.get_or_none(name)

    @property
    def embedding_model(self) -> EmbeddingModel | None:
        try:
            return registry.get("embedding_model")
        except KeyError:
            return None

    @property
    def vector_store(self) -> VectorStore | None:
        try:
            return registry.get("vector_store")
        except KeyError:
            return None

    @property
    def memory(self) -> Memory | None:
        try:
            return registry.get("memory")
        except KeyError:
            return None

    @property
    def doc_loader(self) -> DocumentLoader | None:
        try:
            return registry.get("doc_loader")
        except KeyError:
            return None

    @property
    def llm(self) -> LLM | None:
        try:
            return registry.get("llm")
        except KeyError:
            return None

    @property
    def kb_manager(self) -> KnowledgeBaseManager | None:
        try:
            return registry.get("kb_manager")
        except KeyError:
            return None

    @property
    def orchestrator(self) -> SupportGraph | None:
        try:
            return registry.get("orchestrator")
        except KeyError:
            return None


container = Container()
