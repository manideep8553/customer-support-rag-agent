# Customer Support RAG Agent with Conversational Memory

A production-ready, intelligent customer support chatbot powered by **Retrieval-Augmented Generation (RAG)** with full conversational memory. Built for a fictional company, **GigaCorp**, this system answers policy-related customer queries by retrieving relevant knowledge from a local document store while maintaining multi-turn conversation context.

---

## Features

- **RAG-Based Question Answering** — Retrieves relevant policy sections from a knowledge base and generates accurate, context-aware responses.
- **Conversational Memory** — Maintains multi-turn conversation history per session with JSON-based persistence across restarts.
- **Multi-Session Management** — Create, list, view history, and delete conversations.
- **Source Citations** — Every answer includes links to the retrieved source content with relevance scores.
- **Knowledge Base Ingestion** — Automatically loads and chunks Markdown documents on startup; supports manual re-ingestion via API.
- **10+ Intent Handlers** — Specialized answers for refunds, shipping, warranty, billing, pricing, licensing, support, SLA, privacy, and trials.
- **Modern Web UI** — Clean, responsive chat interface with session sidebar, source viewer modal, and typing indicator.
- **RESTful API** — Fully documented API with session management, chat, history, and health endpoints.
- **Modular Architecture** — Clean separation of concerns: RAG engine, memory, knowledge base, API, and frontend.
- **Lightweight Dependencies** — No PyTorch or heavy deep-learning frameworks; uses scikit-learn TF-IDF or FAISS/ChromaDB for fast, CPU-only retrieval.
- **LangGraph Orchestration** — Conversation flow managed by a LangGraph StateGraph with clear node separation (retrieve → route → answer → generate).
- **Ports & Adapters Architecture** — Abstract interfaces for VectorStore, LLM, Memory, and DocumentLoader enable swapping implementations without code changes.
- **Config-Driven Adapter Selection** — Switch between FAISS/ChromaDB, local/cloud LLM, or JSON/Redis memory via `.env` config.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  Browser (HTML/CSS/JS) ────── REST API / SSE ──────▶               │
└─────────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                           │
│  Routes → Validation → Auth (future) → Delegation                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                  ORCHESTRATION (LangGraph StateGraph)               │
│                                                                      │
│  ┌──────────┐   ┌───────┐   ┌──────────┐   ┌──────────┐            │
│  │ Retrieve │──▶│ Route │──▶│ Answer_* │──▶│ Generate │──▶ Response │
│  └────┬─────┘   └───────┘   └──────────┘   └──────────┘            │
│       │                                                            │
└───────┼────────────────────────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────────────────────────────────┐
│                      PORTS (Abstract Interfaces)                    │
│  VectorStore · LLM · Memory · DocumentLoader                        │
└───────┬────────────────────────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────────────────────────────────┐
│                     ADAPTERS (Concrete Implementations)             │
│  FAISS / ChromaDB · Ollama / OpenAI · LangGraph State / JSON       │
└────────────────────────────────────────────────────────────────────┘
```

### Request Flow

1. User sends a message via the web UI or API.
2. **API Routes** validate and dispatch to the **LangGraph StateGraph**.
3. **Retrieve node** queries the **VectorStore** port (FAISS/ChromaDB) for relevant chunks.
4. **Route node** classifies intent via keyword matching (or LLM, if configured).
5. **Answer_* node** builds a templated response using retrieved context.
6. **Generate node** assembles final response with source citations.
7. Response is stored in **Memory** port and returned to the user.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI (Python 3.11+) |
| **ASGI Server** | Uvicorn |
| **Orchestration** | LangGraph StateGraph |
| **Vector Store** | FAISS (default) / ChromaDB (configurable) |
| **Retrieval** | scikit-learn TfidfVectorizer + cosine similarity |
| **Data Validation** | Pydantic v2 |
| **Configuration** | Pydantic Settings |
| **Memory Storage** | LangGraph State / JSON files (configurable) |
| **LLM** | Rule-based (default) / Ollama / OpenAI (configurable) |
| **Tokenization** | tiktoken (OpenAI-compatible) |
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **HTTP Client (API)** | httpx |

---

## Project Structure

```
Customer Support RAG Agent/
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point, lifespan, DI wiring
│   ├── config.py                  # Pydantic-based settings (paths, model config, server)
│   ├── di/
│   │   └── container.py           # Dependency injection container (wires ports → adapters)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # All REST API endpoints (chat, sessions, history, etc.)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic request/response models
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── vector_store.py         # VectorStore protocol (embed, add, search, delete)
│   │   ├── llm.py                  # LLM protocol (generate, stream, count_tokens)
│   │   ├── memory.py               # Memory protocol (sessions, turns, history)
│   │   └── document_loader.py      # DocumentLoader protocol (load, chunk)
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── vector_store/
│   │   │   ├── __init__.py
│   │   │   ├── faiss_adapter.py    # FAISS vector store implementation
│   │   │   └── chroma_adapter.py   # ChromaDB vector store implementation
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── ollama_adapter.py   # Local Ollama LLM implementation
│   │   │   └── openai_adapter.py   # OpenAI LLM implementation
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── langgraph_memory.py # LangGraph state persistence
│   │   │   └── json_file_memory.py # JSON file memory (legacy)
│   │   └── document_loader/
│   │       ├── __init__.py
│   │       └── markdown_loader.py  # Markdown document loader & chunker
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── graph.py               # LangGraph StateGraph builder + SupportGraph class
│   │   ├── state.py                # ConversationState TypedDict
│   │   ├── memory.py               # LangGraph checkpoint integration
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── retrieve.py         # Vector store retrieval node
│   │       ├── route.py            # Intent classification node
│   │       ├── answers.py          # Per-intent answer generators (14 intents)
│   │       └── generate.py         # Final response assembly node
│   ├── memory/                     # (legacy)
│   │   ├── __init__.py
│   │   └── conversation.py
│   ├── rag/                        # (legacy)
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── retriever.py
│   │   └── embedding.py
│   └── knowledge_base/
│       ├── __init__.py
│       └── store.py               # Knowledge base manager (ingest via VectorStore port)
├── frontend/
│   ├── index.html                 # Main chat UI page
│   ├── css/
│   │   └── style.css              # Responsive styles (desktop + mobile)
│   └── js/
│       └── app.js                 # Frontend logic (sessions, messages, sources, events)
├── data/
│   ├── knowledge_base/
│   │   └── gigacorp_policies.md   # GigaCorp's comprehensive policy document (10 sections)
│   └── vector_store/              # Persisted index, sessions, FAISS/ChromaDB data
├── scripts/
│   ├── run.py                     # Convenience script to start the server
│   └── ingest.py                  # Standalone script to ingest/re-ingest documents
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
├── ARCHITECTURE.md                # Full architecture design document
└── README.md                      # This file
```

---

## Prerequisites

- **Python 3.11+** (tested on 3.13)
- **pip** (Python package manager)
- **A modern web browser** (Chrome, Firefox, Safari, Edge)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/customer-support-rag-agent.git
cd customer-support-rag-agent
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
# or
venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Variables

All configuration is managed via environment variables or a `.env` file. Copy the template and customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | GigaCorp Customer Support RAG Agent | Application name |
| `APP_VERSION` | 1.2.0 | Application version |
| `VECTOR_STORE_TYPE` | faiss | Vector store backend: `faiss` or `chromadb` |
| `EMBEDDING_DIM` | 384 | Embedding dimension for FAISS |
| `LLM_PROVIDER` | *(empty)* | LLM backend: `ollama`, `openai`, or empty for rule-based |
| `LLM_MODEL` | *(empty)* | Model name (e.g. `llama3.1:8b`, `gpt-4o-mini`) |
| `MEMORY_BACKEND` | langgraph_state | Memory backend: `langgraph_state` or `json_file` |
| `CHUNK_SIZE` | 512 | Maximum characters per knowledge base chunk |
| `CHUNK_OVERLAP` | 64 | Overlap characters between adjacent chunks |
| `TOP_K_RETRIEVAL` | 4 | Number of relevant chunks to retrieve per query |
| `MEMORY_MAX_TURNS` | 20 | Maximum conversation turns kept in memory |
| `SESSION_TIMEOUT_MINUTES` | 60 | Inactivity timeout for session cleanup |
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8000 | Server port |
| `RELOAD` | true | Auto-reload on code changes (development) |

---

## Setup

The knowledge base is ingested **automatically on startup** from `data/knowledge_base/gigacorp_policies.md`. No manual setup is required.

If you need to re-ingest (e.g., after editing the policy document), use:

```bash
python scripts/ingest.py
```

Or via the API:

```bash
curl -X POST http://localhost:8000/api/v1/ingest
```

---

## Running the Application

### Start the Server

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Or use the convenience script:

```bash
python scripts/run.py
```

The server will:
1. Load and initialize the embedding service and retriever.
2. Ingest the knowledge base documents (if not already indexed).
3. Start serving the API and frontend.

### Access the Application

| Resource | URL |
|----------|-----|
| **Web UI** | [http://localhost:8000](http://localhost:8000) |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **API Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

### Verify It's Running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "knowledge_base": {
    "initialized": true,
    "chunk_count": 65
  },
  "timestamp": "2026-07-14T03:00:00.000000"
}
```

---

## RAG Pipeline Workflow

### 1. Document Ingestion

During startup (or when manually triggered), the pipeline:

1. **Loads** the Markdown policy document from `data/knowledge_base/`.
2. **Splits** the document into semantic sections by markdown headings (`##`, `###`).
3. **Chunks** each section into overlapping segments (512 chars each, 64-char overlap).
4. **Adds** chunks + metadata to the configured **VectorStore** port (FAISS or ChromaDB).
5. **Persists** the index to `data/vector_store/`.

### 2. Query Processing (LangGraph StateGraph)

When a user sends a message, the **LangGraph StateGraph** executes:

**Node 1 — Retrieve:**
1. The query is dispatched to the **VectorStore** port.
2. Cosine similarity search returns the top-K chunks (default: 4) with relevance scores.

**Node 2 — Route:**
1. The query is classified into one of 14 intent categories using keyword matching:
   - Refunds, Shipping, Warranty, Password, Upgrades, Cancellations,
     Billing, Trials, Privacy, Contact, Pricing, Licensing, SLA, Nonprofit
2. The graph routes to the matching answer node (conditional edge).

**Node 3 — Answer_*:**
1. The intent-specific node constructs a templated answer using the retrieved context.
2. If an **LLM** is configured (Ollama/OpenAI), the prompt + context is sent to the LLM instead.

**Node 4 — Generate:**
1. Final response is assembled with source citations.
2. Answer + sources are returned.

### 3. Memory & State Persistence

1. Conversation turns are stored via the **Memory** port (LangGraph State or JSON files).
2. LangGraph checkpoints persist the graph state per session.
3. Sessions are listed, queried, and pruned via the Memory interface.

---

## Conversational Memory

The **ConversationMemory** module provides multi-turn history management:

- **Session-Based**: Each conversation is identified by a unique `session_id`.
- **Thread-Safe**: Uses `threading.Lock` for concurrent access safety.
- **Persistent Storage**: Sessions are saved as individual JSON files in `data/vector_store/sessions/`.
- **Auto-Cleanup**: Stale sessions (exceeding `SESSION_TIMEOUT_MINUTES` of inactivity) are pruned.
- **Context Truncation**: Keeps only the most recent `MEMORY_MAX_TURNS` (40 messages) to manage token usage.

The history is injected into the prompt context for follow-up questions, enabling natural multi-turn conversations like:

```
User: What is your return policy?
Bot: [answers with refund policy]
User: How fast do I get my money back?
Bot: [understands "money back" refers to refunds and follows up accordingly]
```

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Send a message and get an answer |

**Request Body:**
```json
{
  "session_id": "session_abc123",
  "message": "What is your return policy?",
  "stream": false
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "answer": "Based on GigaCorp's Return and Refund Policy...",
  "sources": [
    {
      "content": "## 1. Return and Refund Policy...",
      "score": 0.605,
      "source": "gigacorp_policies.md"
    }
  ],
  "timestamp": "2026-07-14T03:00:00.000000"
}
```

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions` | Create a new session |
| `GET` | `/api/v1/sessions` | List all sessions |
| `GET` | `/api/v1/sessions/{id}` | Get session info |
| `DELETE` | `/api/v1/sessions/{id}` | Delete a session |
| `POST` | `/api/v1/sessions/{id}/history` | Get message history |

### Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest` | Ingest/re-ingest knowledge base |
| `GET` | `/api/v1/health` | Health check with KB status |

---

## Knowledge Base

The default knowledge base is a comprehensive policy document for **GigaCorp** located at `data/knowledge_base/gigacorp_policies.md`. It covers 10 major sections:

1. **Return and Refund Policy** — 30-day refunds, hardware returns, enterprise contracts
2. **Shipping and Delivery** — Standard/Express/Next-Day tiers, international
3. **Warranty Policy** — Software/hardware coverage periods and exclusions
4. **Account and Billing** — Account types, payment methods, late fees
5. **Subscription and Licensing** — Perpetual/subscription/concurrent licenses
6. **Technical Support** — Three tiers (Basic/Priority/Premium), severity levels
7. **Privacy Policy** — Data collection, GDPR compliance, security measures
8. **Terms of Service** — Acceptable use, SLA, liability limits
9. **Product Catalog** — Cloud services, AI platform, enterprise software, hardware
10. **FAQ** — Password reset, upgrades, trials, non-profit discounts

### Customizing the Knowledge Base

1. Edit `data/knowledge_base/gigacorp_policies.md` or add new `.md` files.
2. Re-ingest:
   ```bash
   python scripts/ingest.py
   ```
   Or restart the server (auto-ingests on startup).

The knowledge base supports any Markdown content. Documents are chunked by headings (`#`, `##`, `###`), so organizing your content with clear headings improves retrieval accuracy.

---

## Usage Examples

### Via the Web UI

1. Open [http://localhost:8000](http://localhost:8000) in your browser.
2. Type a question in the input box, for example:
   - _"What is your return policy?"_
   - _"How much does GigaAnalytics cost?"_
   - _"What support tiers do you offer?"_
   - _"How do I reset my password?"_
3. Click a suggestion chip to ask a common question.
4. View source citations by clicking the source badges below each answer.
5. Start a new conversation using the **New Chat** button in the sidebar.

### Via the API

```bash
# Create a session
curl -X POST http://localhost:8000/api/v1/sessions

# Ask a question
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<your-session-id>", "message": "What is your warranty policy?"}'

# View conversation history
curl -X POST http://localhost:8000/api/v1/sessions/<session-id>/history \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<your-session-id>", "limit": 50}'
```

---

## Screenshots

> *Screenshots would be added here in a real project. Below are placeholders describing what each one would show.*

### Chat Interface
![Chat Interface](docs/screenshots/chat-interface.png)
*The main chat window showing a conversation with GigaBot, including user messages, bot responses, and source citation badges.*

### Session Management
![Session Sidebar](docs/screenshots/session-sidebar.png)
*The sidebar listing active conversations with the ability to switch between sessions or create new ones.*

### Source Viewer
![Source Citations](docs/screenshots/source-viewer.png)
*A modal dialog showing the retrieved knowledge base chunks with relevance scores that were used to generate a response.*

---

## Troubleshooting

### Server Won't Start

**Issue**: `ModuleNotFoundError: No module named 'pydantic_settings'`

**Solution**: Ensure your virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

**Issue**: `Address already in use` / port 8000 is occupied

**Solution**: Kill the existing process or use a different port:
```bash
# Find and kill the process
lsof -i :8000
kill -9 <PID>

# Or use a different port
python -m uvicorn backend.main:app --port 8001
```

### Chat Returns No Relevant Information

**Issue**: The bot responds with "I don't have enough information" even for known topics.

**Solution**: Re-ingest the knowledge base:
```bash
python scripts/ingest.py
```

Or check that `data/knowledge_base/gigacorp_policies.md` exists and is not empty.

### Slow Response Times

The TF-IDF retrieval is designed for fast CPU-only operation. If queries are slow:
- Reduce `TOP_K_RETRIEVAL` in your `.env` file (default: 4).
- Reduce `CHUNK_SIZE` to create smaller, more targeted chunks.
- Ensure your system is not under heavy memory pressure.

### Session History Not Loading

If the API returns 404 for session history:
- Ensure you're using the correct `session_id`.
- Sessions are stored in `data/vector_store/sessions/`. If this directory was deleted, sessions are lost permanently.

---

## Future Enhancements

- [ ] **LLM Integration** — Replace rule-based response generation with a local or cloud LLM (e.g., Llama, GPT-4) for more natural and flexible answers.
- [ ] **Streaming Responses** — Implement Server-Sent Events (SSE) for real-time token-by-token response streaming.
- [ ] **Vector Database Upgrade** — Replace in-memory TF-IDF with ChromaDB, Qdrant, or Pinecone for better scalability.
- [ ] **Authentication** — Add user authentication and role-based access control.
- [ ] **Admin Dashboard** — Dashboard for monitoring queries, session analytics, and knowledge base management.
- [ ] **Multi-Language Support** — Internationalize the UI and add multilingual knowledge base support.
- [ ] **Docker Deployment** — Provide `Dockerfile` and `docker-compose.yml` for containerized deployment.
- [ ] **Evaluation Framework** — Add test harness for measuring retrieval accuracy and response quality.
- [ ] **Webhook Integration** — Connect to external ticketing systems (Zendesk, Freshdesk) for seamless escalation.
- [ ] **Conversation Export** — Allow users to download conversation transcripts as PDF or JSON.

---

## Contributing

Contributions are welcome! Here's how to get involved:

1. **Fork** the repository.
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the existing code style and conventions.
4. **Run the tests**: `python -m pytest` (ensure existing tests pass).
5. **Commit** your changes with a clear, descriptive message.
6. **Push** to your fork: `git push origin feature/amazing-feature`
7. **Open a Pull Request** describing your changes in detail.

### Development Guidelines

- Maintain the modular architecture — each component should have a single responsibility.
- Add type hints to all new Python code.
- Update the API documentation if adding or modifying endpoints.
- Write or update tests for any new functionality.
- Keep the frontend dependency-free (no build step, no npm).

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

*Built with FastAPI, scikit-learn, and vanilla JavaScript.*
*Created for demonstration and educational purposes.*
