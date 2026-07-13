# Architecture — Customer Support RAG Agent

## Design Philosophy

The system is built on **Hexagonal Architecture (Ports & Adapters)** combined with a **LangGraph-powered orchestration layer**. Every core capability is defined as an abstract **Port (interface)** with multiple **Adapter** implementations, enabling any component (vector store, LLM, memory backend, document loader) to be swapped without modifying business logic.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────────────────┐              │
│  │  Web UI (SPA)    │────▶│     FastAPI REST API         │              │
│  │  HTML/CSS/JS     │     │  + WebSocket / SSE streaming │              │
│  └──────────────────┘     └───────────┬──────────────────┘              │
│                                        │                                │
└────────────────────────────────────────┼────────────────────────────────┘
                                         │
┌────────────────────────────────────────┼────────────────────────────────┐
│                          APPLICATION LAYER                              │
│                                         │                               │
│  ┌──────────────────────────────────────▼────────────────────────────┐  │
│  │              ORCHESTRATION LAYER (LangGraph)                      │  │
│  │                                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │ Conversation │  │  Graph Nodes │  │   Graph      │            │  │
│  │  │  Graph       │──│ • retrieve   │──│  Compiler    │──▶ State   │  │
│  │  │ (StateGraph) │  │ • generate   │  │ (checkpoint) │   Snapshot │  │
│  │  │              │  │ • route      │  │              │            │  │
│  │  │              │  │ • rewrite    │  │              │            │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘            │  │
│  └─────────┼─────────────────┼──────────────────────────────────────┘  │
│            │                 │                                          │
└────────────┼─────────────────┼──────────────────────────────────────────┘
             │                 │
┌────────────┼─────────────────┼──────────────────────────────────────────┐
│            │     PORT INTERFACES (Abstractions Layer)                   │
│            ▼                 ▼                                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ VectorStore  │  │      LLM        │  │   Memory   │  │  Doc     │  │
│  │  (Port)     │  │   (Port)        │  │  (Port)    │  │  Loader  │  │
│  │             │  │                  │  │            │  │  (Port)  │  │
│  │embed/       │  │generate()       │  │add_turn()  │  │load()    │  │
│  │search()     │  │stream()         │  │get_history│  │chunk()   │  │
│  │delete()     │  │                 │  │clear()     │  │          │  │
│  └──────┬──────┘  └───────┬──────────┘  └─────┬──────┘  └────┬─────┘  │
│         │                 │                    │              │        │
│  ┌──────▼──────┐  ┌───────▼──────────┐  ┌─────▼──────┐  ┌────▼─────┐  │
│  │ FAISSAdapter │  │ OllamaAdapter   │  │ LangGraph  │  │Markdown  │  │
│  │ChromaDBAdapt.│  │ OpenAIAdapter   │  │ StateMem   │  │Loader    │  │
│  │PineconeAdapt.│  │ AnthropicAdapter│  │ RedisMem   │  │PDFLoader │  │
│  │ (future)     │  │ (future)        │  │ (future)   │  │ (future) │  │
│  └──────────────┘  └─────────────────┘  └────────────┘  └──────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                         │           │            │
┌────────────────────────┼───────────┼────────────┼────────────────────────┐
│               INFRASTRUCTURE LAYER                                       │
│                        ▼           ▼            ▼                       │
│  ┌──────────────┐  ┌──────────┐  ┌────────┐  ┌────────────────────┐   │
│  │  ChromaDB    │  │  Ollama  │  │ SQLite │  │  AWS Bedrock       │   │
│  │  FAISS       │  │  OpenAI  │  │ Redis  │  │  GCP Vertex AI     │   │
│  │  (local)     │  │  (local) │  │ (future)│  │  Azure AI (future) │   │
│  └──────────────┘  └──────────┘  └────────┘  └────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Details

### 1. Presentation Layer (Frontend)

- **SPA** built with vanilla HTML/CSS/JS (zero dependencies).
- Communicates via **REST APIs** (`/api/v1/*`) and **Server-Sent Events** (`/api/v1/chat/stream`).
- WebSocket-ready for future real-time features.

### 2. Application Layer (API Gateway)

- **FastAPI** server with CORS, middleware, and route registration.
- No business logic — purely routing, validation (Pydantic), and delegation to the orchestration layer.
- Pluggable auth middleware (future: JWT, API keys, OAuth2).

### 3. Orchestration Layer (LangGraph)

Replaces the previous monolithic `RAGEngine` with a **LangGraph StateGraph** workflow:

```
                    ┌──────────┐
                    │  ENTRY   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ retrieve │─── VectorStore (Port)
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  route   │─── Intent classifier
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼───┐ ┌───▼───┐
         │answer  │ │answer │ │answer │ ... (per intent)
         │refund  │ │ship   │ │general│
         └────┬───┘ └───┬───┘ └───┬───┘
              │          │          │
              └──────────┼──────────┘
                         │
                    ┌────▼─────┐
                    │ generate │─── LLM (Port)
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  EXIT    │
                    └──────────┘
```

**Graph State** (TypedDict):

```python
class ConversationState(TypedDict):
    messages: list[BaseMessage]      # LangChain message history
    session_id: str
    query: str
    retrieved_docs: list[Document]
    context: str
    intent: str | None
    answer: str
    sources: list[dict]
    next_node: str
```

- **`retrieve`** node: embeds query, searches vector store, returns top-K chunks.
- **`route`** node: classifies query intent via LLM or keyword matching.
- **`answer_*`** nodes: per-intent answer templates (can be LLM-generated).
- **`generate`** node: final response assembly with source citations.
- Conditional edges based on intent classification.

### 4. Ports & Adapters (Abstractions Layer)

Every external dependency is behind a **Port** (abstract protocol):

| Port | Responsibilities | Adapters |
|------|-----------------|----------|
| `VectorStore` | `embed()`, `search()`, `add()`, `delete()`, `clear()` | `FAISSAdapter`, `ChromaDBAdapter` |
| `LLM` | `generate()`, `stream()`, `count_tokens()` | `OllamaAdapter`, `OpenAIAdapter` |
| `Memory` | `add_turn()`, `get_history()`, `get_messages()`, `list_sessions()`, `delete_session()`, `clear()` | `LangGraphMemoryAdapter`, `RedisMemoryAdapter` |
| `DocumentLoader` | `load()`, `chunk()`, `supported_extensions()` | `MarkdownLoader`, `PDFLoader` |

**New adapter = no code changes in orchestration.** Just implement the Port and register it in the DI container.

### 5. Infrastructure Layer

- **Vector Database**: ChromaDB (local, persistent) or FAISS (in-memory with persistence).
- **Session Storage**: Currently JSON files; swappable to PostgreSQL, Redis, or cloud DB via Memory port.
- **LLM Backend**: Configurable between local (Ollama) and cloud (OpenAI, Anthropic).

---

## Dependency Injection

A simple DI container (`backend/di/container.py`) wires everything together at startup:

```python
# config-driven adapter selection
vector_store = FAISSAdapter(embedding_dim=384)
if settings.vector_store_type == "chromadb":
    vector_store = ChromaDBAdapter(persist_dir=settings.vector_store_path)

llm = OllamaAdapter(model=settings.llm_model)
if settings.llm_provider == "openai":
    llm = OpenAIClient(api_key=settings.openai_api_key)

memory = LangGraphMemoryAdapter(max_turns=settings.memory_max_turns)

doc_loader = MarkdownLoader(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
kb_manager = KnowledgeBaseManager(vector_store=vector_store, doc_loader=doc_loader)

orchestrator = SupportGraph(
    vector_store=vector_store,
    llm=llm,
    memory=memory,
)
```

Changing vector store, LLM, or memory backend requires **no code changes beyond config**.

---

## Directory Structure (Refactored)

```
backend/
├── main.py                        # FastAPI entry point, DI wiring
├── config.py                      # Pydantic Settings
├── di/
│   └── container.py               # Dependency injection container
├── api/
│   ├── __init__.py
│   └── routes.py                  # REST endpoints
├── models/
│   ├── __init__.py
│   └── schemas.py                 # Pydantic schemas
├── orchestration/
│   ├── __init__.py
│   ├── graph.py                   # LangGraph StateGraph definition
│   ├── state.py                   # ConversationState TypedDict
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── retrieve.py            # Vector store retrieval node
│   │   ├── route.py               # Intent classification node
│   │   ├── answers.py             # Per-intent answer generators
│   │   └── generate.py            # Final response assembly
│   └── memory.py                  # LangGraph memory integration
├── ports/
│   ├── __init__.py
│   ├── vector_store.py            # VectorStore protocol
│   ├── llm.py                     # LLM protocol
│   ├── memory.py                  # Memory protocol
│   └── document_loader.py         # DocumentLoader protocol
├── adapters/
│   ├── __init__.py
│   ├── vector_store/
│   │   ├── __init__.py
│   │   ├── faiss_adapter.py       # FAISS implementation
│   │   └── chroma_adapter.py      # ChromaDB implementation
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama_adapter.py      # Ollama (local) implementation
│   │   └── openai_adapter.py      # OpenAI implementation
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── langgraph_memory.py    # LangGraph state persistence
│   │   └── json_file_memory.py    # Legacy JSON file memory
│   └── document_loader/
│       ├── __init__.py
│       └── markdown_loader.py     # Markdown loader (from legacy)
├── knowledge_base/
│   ├── __init__.py
│   └── store.py                   # Ingestion coordinator
└── legacy/                        # (temporary) original modules
    └── ...
```

---

## Data Flow (Request Lifecycle)

```
User Message
    │
    ▼
[POST /api/v1/chat {session_id, message}]
    │
    ▼
[API Routes] ── validate with Pydantic
    │
    ▼
[SupportGraph.invoke(message, session_id)]
    │
    ├─▶ [retrieve node]  ── VectorStore.search(query) ──▶ top-K chunks
    │
    ├─▶ [route node]    ── Intent classifier (LLM / keyword)
    │
    ├─▶ [answer_* node] ── Build answer with retrieved context
    │
    ├─▶ [generate node] ── Assemble response + sources
    │
    └─▶ return {answer, sources, session_id}
    │
    ▼
[JSON Response] ──▶ User
```

## Streaming Flow

```
POST /api/v1/chat/stream {session_id, message}
    │
    ▼
[SSE Response]
    │
    ├─▶ event: token   data: "Based on..."
    ├─▶ event: token   data: " GigaCorp's..."
    ├─▶ event: source  data: {"content": "...", "score": 0.95}
    └─▶ event: done    data: {"session_id": "...", "finish_reason": "stop"}
```

---

## Future Integration Points

| Component | Current | Future Option | Integration Point |
|-----------|---------|--------------|-------------------|
| **Vector Store** | FAISS | ChromaDB, Pinecone, Qdrant, Weaviate | `VectorStore` port |
| **LLM** | Ollama/Local | OpenAI, Anthropic Claude, AWS Bedrock, GCP Vertex AI, Azure OpenAI | `LLM` port |
| **Memory** | LangGraph State | Redis, PostgreSQL, MongoDB, DynamoDB | `Memory` port |
| **Document Loader** | Markdown | PDF, HTML, DocX, Confluence, Notion, SharePoint | `DocumentLoader` port |
| **Authentication** | None | JWT, OAuth2, API Keys, SAML | FastAPI middleware |
| **Database** | JSON files | PostgreSQL, SQLite, MySQL, CockroachDB | `Memory` port + SQLAlchemy |
| **Monitoring** | Logging | OpenTelemetry, Prometheus, Datadog, Sentry | FastAPI middleware + DI |
| **Enterprise APIs** | None | Zendesk, Freshdesk, Salesforce, Jira | Custom LangGraph tools |
| **Admin Dashboard** | None | FastAPI Admin, React Admin | Separate frontend app |
| **Evaluation** | Manual | LangSmith, MLflow, custom eval harness | LangGraph callbacks |

---

## Configuration-Driven Architecture

Every architectural choice is driven by `.env`:

```env
# --- Vector Store ---
VECTOR_STORE_TYPE=faiss              # faiss | chromadb | (future: pinecone, qdrant)
VECTOR_STORE_PATH=data/vector_store  # local persistence path
EMBEDDING_DIM=384                    # embedding dimension

# --- LLM ---
LLM_PROVIDER=ollama                  # ollama | openai | anthropic | (future: bedrock, vertex)
LLM_MODEL=llama3.1:8b                # model name
OPENAI_API_KEY=                      # required if LLM_PROVIDER=openai
ANTHROPIC_API_KEY=                   # required if LLM_PROVIDER=anthropic

# --- Memory ---
MEMORY_BACKEND=langgraph_state       # langgraph_state | json_file | (future: redis, postgres)

# --- RAG ---
CHUNK_SIZE=512
CHUNK_OVERLAP=64
TOP_K_RETRIEVAL=4
MEMORY_MAX_TURNS=20
SESSION_TIMEOUT_MINUTES=60

# --- Server ---
HOST=0.0.0.0
PORT=8000
RELOAD=true
```

Switching from FAISS to ChromaDB is a single `.env` change: `VECTOR_STORE_TYPE=chromadb`. No code changes. No redeploy. Just restart.
