import logging

from backend.config import settings
from backend.ports.vector_store import VectorStore
from backend.ports.memory import Memory
from backend.ports.document_loader import DocumentLoader
from backend.ports.llm import LLM

from backend.adapters.vector_store.faiss_adapter import FAISSAdapter
from backend.adapters.vector_store.chroma_adapter import ChromaDBAdapter
from backend.adapters.memory.langgraph_memory import LangGraphMemory
from backend.adapters.memory.json_file_memory import JsonFileMemory
from backend.adapters.chunking.langchain_splitter import LangChainMarkdownLoader

from backend.knowledge_base.store import KnowledgeBaseManager
from backend.orchestration.graph import SupportGraph
from backend.errors import ConfigurationError, log_exception

logger = logging.getLogger("gigacorp.di")


class Container:
    def __init__(self):
        self.embedding_model = None
        self.vector_store: VectorStore | None = None
        self.memory: Memory | None = None
        self.doc_loader: DocumentLoader | None = None
        self.llm: LLM | None = None
        self.kb_manager: KnowledgeBaseManager | None = None
        self.orchestrator: SupportGraph | None = None

        self._init_all()

    def _init_all(self):
        try:
            self.embedding_model = self._init_embedding()
        except Exception as e:
            log_exception(e, "Container.embedding")
            logger.critical("Failed to initialize embedding model. The system cannot start.")
            raise

        try:
            self.vector_store = self._init_vector_store()
        except Exception as e:
            log_exception(e, "Container.vector_store")
            logger.critical("Failed to initialize vector store. The system cannot start.")
            raise

        try:
            self.doc_loader = self._init_doc_loader()
        except Exception as e:
            log_exception(e, "Container.doc_loader")
            logger.critical("Failed to initialize document loader. The system cannot start.")
            raise

        self.memory = self._init_memory()
        self.llm = self._init_llm()
        self.kb_manager = self._init_kb_manager()

        try:
            self.orchestrator = self._init_orchestrator()
        except Exception as e:
            log_exception(e, "Container.orchestrator")
            logger.critical("Failed to initialize orchestrator. The system cannot start.")
            raise

        self._log_summary()

    def _log_summary(self):
        llm_status = f"{settings.llm_provider or 'rule-based'}" if self.llm else "rule-based"
        logger.info(
            "Container initialized | Embedding: %s/%s | Vector: %s | Memory: %s | LLM: %s",
            settings.embedding_provider, settings.embedding_model,
            settings.vector_store_type,
            settings.memory_backend,
            llm_status,
        )

    def _init_embedding(self):
        provider = settings.embedding_provider
        model = settings.embedding_model
        logger.info("Initializing embedding model: %s (%s)", provider, model)
        if provider == "openai":
            from backend.adapters.embeddings.openai_embedding import OpenAIEmbedding
            return OpenAIEmbedding(model_name=model, api_key=settings.openai_api_key)
        if provider == "huggingface":
            from backend.adapters.embeddings.hf_embedding import HFEmbedding
            return HFEmbedding(model_name=model)
        raise ConfigurationError(f"Unknown embedding provider: {provider}")

    def _init_vector_store(self) -> VectorStore:
        vs_type = settings.vector_store_type
        logger.info("Initializing vector store: %s", vs_type)
        if vs_type == "chromadb":
            return ChromaDBAdapter(embedding_model=self.embedding_model)
        if vs_type == "faiss":
            return FAISSAdapter(embedding_model=self.embedding_model)
        raise ConfigurationError(f"Unknown vector store type: {vs_type}")

    def _init_memory(self) -> Memory:
        backend = settings.memory_backend
        logger.info("Initializing memory backend: %s", backend)
        try:
            if backend == "json_file":
                return JsonFileMemory()
            return LangGraphMemory()
        except Exception as e:
            logger.error("Failed to initialize %s memory, falling back to LangGraphMemory: %s", backend, e)
            return LangGraphMemory()

    def _init_doc_loader(self) -> DocumentLoader:
        return LangChainMarkdownLoader()

    def _init_llm(self) -> LLM | None:
        provider = settings.llm_provider
        if not provider:
            logger.info("No LLM provider configured \u2014 using rule-based answers")
            return None
        logger.info("Initializing LLM provider: %s", provider)
        try:
            if provider == "openai":
                if not settings.openai_api_key:
                    logger.warning("OpenAI provider selected but no API key configured. Falling back to rule-based.")
                    return None
                from backend.adapters.llm.openai_adapter import OpenAIAdapter
                return OpenAIAdapter(model=settings.llm_model or "gpt-4o-mini")
            if provider == "ollama":
                from backend.adapters.llm.ollama_adapter import OllamaAdapter
                return OllamaAdapter(model=settings.llm_model or "llama3.1:8b")
            logger.warning("Unknown LLM provider: %s", provider)
            return None
        except Exception as e:
            logger.error("Failed to initialize LLM provider %s: %s. Falling back to rule-based.", provider, e)
            return None

    def _init_kb_manager(self) -> KnowledgeBaseManager:
        return KnowledgeBaseManager(vector_store=self.vector_store, doc_loader=self.doc_loader)

    def _init_orchestrator(self) -> SupportGraph:
        return SupportGraph(
            vector_store=self.vector_store,
            memory_backend=self.memory,
            llm=self.llm,
        )


container = Container()
