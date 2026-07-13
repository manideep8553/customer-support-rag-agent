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

logger = logging.getLogger("gigacorp.di")


class Container:
    def __init__(self):
        self.embedding_model = self._init_embedding()
        self.vector_store: VectorStore = self._init_vector_store()
        self.memory: Memory = self._init_memory()
        self.doc_loader: DocumentLoader = self._init_doc_loader()
        self.llm: LLM | None = self._init_llm()
        self.kb_manager: KnowledgeBaseManager = self._init_kb_manager()
        self.orchestrator: SupportGraph = self._init_orchestrator()

    def _init_embedding(self):
        provider = settings.embedding_provider
        model = settings.embedding_model
        logger.info("Initializing embedding model: %s (%s)", provider, model)
        if provider == "openai":
            from backend.adapters.embeddings.openai_embedding import OpenAIEmbedding
            return OpenAIEmbedding(model_name=model, api_key=settings.openai_api_key)
        from backend.adapters.embeddings.hf_embedding import HFEmbedding
        return HFEmbedding(model_name=model)

    def _init_vector_store(self) -> VectorStore:
        vs_type = settings.vector_store_type
        logger.info("Initializing vector store: %s", vs_type)
        if vs_type == "chromadb":
            return ChromaDBAdapter(embedding_model=self.embedding_model)
        return FAISSAdapter(embedding_model=self.embedding_model)

    def _init_memory(self) -> Memory:
        backend = settings.memory_backend
        logger.info("Initializing memory backend: %s", backend)
        if backend == "json_file":
            return JsonFileMemory()
        return LangGraphMemory()

    def _init_doc_loader(self) -> DocumentLoader:
        return LangChainMarkdownLoader()

    def _init_llm(self) -> LLM | None:
        provider = settings.llm_provider
        if not provider:
            logger.info("No LLM provider configured — using rule-based answers")
            return None
        logger.info("Initializing LLM provider: %s", provider)
        if provider == "openai":
            from backend.adapters.llm.openai_adapter import OpenAIAdapter
            return OpenAIAdapter(model=settings.llm_model or "gpt-4o-mini")
        if provider == "ollama":
            from backend.adapters.llm.ollama_adapter import OllamaAdapter
            return OllamaAdapter(model=settings.llm_model or "llama3.1:8b")
        logger.warning("Unknown LLM provider: %s", provider)
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
