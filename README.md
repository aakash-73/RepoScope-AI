<p align="center">
  <img src="frontend/src/logo/logo.png" alt="RepoScope AI Logo" width="300" />
</p>

<h1 align="center">RepoScope AI</h1>

<p align="center">
  <b>AI-Powered Code Architecture Intelligence Platform</b><br/>
  Understand any GitHub repository in minutes — not hours.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" />
  <img alt="MongoDB" src="https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white" />
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-Local_LLM-000000?logo=ollama&logoColor=white" />
  <img alt="Vite" src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green" />
</p>

---

## 📖 What Is RepoScope AI?

RepoScope AI is an **AI-powered code architecture intelligence platform** that transforms any public GitHub repository into an interactive, explorable dependency graph with deep AI-driven analysis.

### The Problem

Understanding a new codebase is painful. Developers spend **hours reading through unfamiliar code**, tracing import chains, figuring out which files matter, and trying to build a mental model of the architecture. Documentation — if it exists — is often outdated.

### The Solution

Give RepoScope AI a GitHub URL and it will:

1. **Download and parse** every source file (80+ file extensions, ~30 languages)
2. **Build an interactive dependency graph** showing how files relate through imports
3. **Run AI analysis on every node** — purpose, patterns, concerns, architectural role
4. **Generate a repo-level understanding** — tech stack, data flow, architecture, entry points
5. **Let you chat** with an AI about any file or the entire repository

The result: a **living, queryable knowledge base** for any codebase, built in minutes.

---

## 🛠️ Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| [React 18](https://react.dev) | UI framework |
| [Vite 5](https://vitejs.dev) | Build tool & dev server |
| [React Flow](https://reactflow.dev) (`@xyflow/react`) | Interactive dependency graph canvas |
| [Framer Motion](https://www.framer.com/motion/) | Animations (node materialization, transitions) |
| [Tailwind CSS 3](https://tailwindcss.com) | Utility-first styling |
| [Lucide React](https://lucide.dev) | Icon library |
| [Axios](https://axios-http.com) | HTTP client |
| [React Router 6](https://reactrouter.com) | Client-side routing |
| [React Markdown](https://github.com/remarkjs/react-markdown) | Markdown rendering in chat |
| [Dagre](https://github.com/dagrejs/dagre) | Directed graph layout algorithm |

### Backend

| Technology | Purpose |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com) | Async Python API framework |
| [Uvicorn](https://www.uvicorn.org) | ASGI server |
| [Motor](https://motor.readthedocs.io) | Async MongoDB driver |
| [Pydantic v2](https://docs.pydantic.dev) | Data validation & settings management |
| [httpx](https://www.python-httpx.org) | Async HTTP client (GitHub API) |
| [OpenAI SDK](https://github.com/openai/openai-python) | Ollama / Groq LLM integration (OpenAI-compatible) |
| [Tree-sitter](https://tree-sitter.github.io) | Multi-language code parsing |

### Database

| Technology | Purpose |
|---|---|
| [MongoDB Atlas](https://www.mongodb.com/atlas) | Cloud-hosted document database |
| [Motor](https://motor.readthedocs.io) | Async Python driver for MongoDB |

### AI / LLM

| Technology | Purpose |
|---|---|
| [Ollama](https://ollama.ai) (Primary) | Self-hosted local LLM inference (`qwen2.5-coder:7b-instruct`) |
| [Groq](https://groq.com) (Fallback) | Cloud LLM API (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) |

### DevOps / Tools

| Technology | Purpose |
|---|---|
| [PM2](https://pm2.keymetrics.io) | Production process manager |
| [pytest](https://docs.pytest.org) | Backend testing framework |
| [Vitest](https://vitest.dev) | Frontend testing framework |
| [Git](https://git-scm.com) | Version control |

---

## ✨ Features

### Core Intelligence

- **🔗 Interactive Dependency Graph** — Visualize how every file in a repo connects through imports/exports in a zoomable, pannable React Flow canvas
- **🤖 Per-Node AI Analysis** — Every file is analyzed by an LLM for purpose, architectural role, patterns, concerns, and a one-line summary for dependents
- **🧠 Repo-Level Understanding** — Synthesized overview of the entire repository: tech stack, architecture, entry points, data flow, and key components
- **💬 AI Chat (File + Repo Level)** — Ask freeform questions about any individual file or the entire repository's architecture
- **🔍 Proactive Insights** — AI surfaces 3–5 actionable insights (coupling hotspots, architectural concerns, notable patterns) without being asked

### Analysis & Detection

- **🔄 Circular Dependency Detection** — DFS cycle detection highlights import loops with animated red edges
- **👻 Dead Code Detection** — Flags files with zero importers that aren't entry points
- **🧪 Test Coverage Overlay** — Shows which source files are imported by test files (green shields)
- **📊 Complexity Scoring** — 1–10 complexity score per file with flame-colored progress bars
- **🔗 Coupling Analysis** — Bidirectional import pairs scored and visualized via edge stroke width
- **💥 Impact Analysis** — For any selected file: "X files could break if you change this" with transitive BFS traversal

### Visual & UX

- **✨ Dynamic Architectural Materialization** — Nodes start ghosted (blueprint) and "solidify" in real-time as the AI finishes analysis, with spring animations
- **📡 Real-Time SSE Streaming** — Server-Sent Events stream analysis progress live (no polling)
- **📊 Progress UI** — Floating progress bar, toast notifications, and inline mini-progress in the repo list
- **🎨 Language Color Legend** — Per-language color coding with customizable color picker
- **🔎 Graph Search** — Fuzzy filename search with highlight-and-jump
- **📤 Graph Export** — Export as PNG (1x/2x/4x), SVG, or JSON
- **🗂️ Folder Grouping** — Nodes visually grouped by directory
- **🔄 Repository Sync** — Incremental sync with GitHub (only re-analyzes changed files + their dependents)

### Language Support

Supports **80+ file extensions** across **~30 languages** including:

> JavaScript · TypeScript · React (JSX/TSX) · Python · Java · Kotlin · Go · Rust · C/C++ · C# · Swift · Dart · Ruby · Vue · Svelte · Elixir · Haskell · Scala · SQL · GraphQL · Terraform · GLSL/WGSL — and many more

---

## 🚀 Installation & Setup

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.11 | [python.org](https://python.org) |
| Node.js | ≥ 20 LTS | [nodejs.org](https://nodejs.org) |
| npm | ≥ 10 | Bundled with Node.js |
| Ollama | Latest | [ollama.ai](https://ollama.ai) |
| Git | Any | [git-scm.com](https://git-scm.com) |
| MongoDB Atlas | Free tier (M0) | [cloud.mongodb.com](https://cloud.mongodb.com) |

### 1. Clone the Repository

```bash
git clone https://github.com/aakash-73/RepoScope-AI.git
cd RepoScope-AI
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI, Ollama config, and (optional) GitHub token
```

### 3. Pull the Ollama Model

```bash
# Make sure Ollama is running
ollama serve

# Pull the analysis model (requires ~4.5GB)
ollama pull qwen2.5-coder:7b-instruct
```

### 4. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

### 5. Start the Application

**Terminal 1 — Ollama** (if not already running):
```bash
ollama serve
```

**Terminal 2 — Backend**:
```bash
cd backend
source .venv/bin/activate    # or .venv\Scripts\activate on Windows
python main.py
# ✅ http://localhost:8000
```

**Terminal 3 — Frontend**:
```bash
cd frontend
npm run dev
# ✅ http://localhost:5173
```

---

## 📋 Usage

### Importing a Repository

1. Open `http://localhost:5173` in your browser
2. Click **"Import Repository"** in the left sidebar
3. Paste a public GitHub URL (e.g. `https://github.com/expressjs/express`)
4. Choose a branch (defaults to `main`, auto-falls back to `master`/`develop`/`dev`)
5. Click **Import** — the dependency graph appears as a ghosted blueprint
6. Watch nodes **materialize in real-time** as the AI analyzes each file

### Exploring the Graph

- **Click a node** → opens the right sidebar with file details, AI analysis, impact analysis, and chat
- **Double-click a node** → triggers AI re-analysis for that specific file
- **Search** → `Ctrl+K` or the search bar to find files by name
- **Export** → Download the graph as PNG, SVG, or JSON

### Chatting with the AI

- **File-level chat** → Select a node → Chat tab in the sidebar → Ask about that specific file
- **Repo-level chat** → Click the floating chat button → Ask about the entire repository's architecture
- **Proactive insights** → Displayed automatically in the repo chat panel

### Syncing with GitHub

- Click the **sync icon** next to a repo → Only changed files are re-downloaded and re-analyzed
- Dependents of changed files are automatically re-analyzed to keep context accurate

---

## 🏗️ Architecture / System Design

### High-Level Architecture

```mermaid
graph TB
    subgraph Client["Frontend (React + Vite)"]
        UI["GraphPage.jsx"]
        Canvas["React Flow Canvas"]
        Sidebar["ComponentSidebar"]
        Chat["RepoChatPanel"]
    end

    subgraph Server["Backend (FastAPI)"]
        Router["API Router"]
        RC["Repo Controller"]
        RCC["Repo Chat Controller"]
        
        subgraph Services["Service Layer"]
            GH["GitHub Service"]
            SC["Smart Classifier"]
            AN["Analyzer Service"]
            GB["Graph Builder"]
            NA["Node Analyzer"]
            GS["Groq / Ollama Service"]
            RCS["Repo Chat Service"]
            SS["Sync Service"]
        end
    end

    subgraph LLM["AI Layer"]
        Ollama["Ollama (Local)"]
        Groq["Groq API (Cloud Fallback)"]
    end

    subgraph DB["MongoDB Atlas"]
        repos[("repositories")]
        files[("files")]
        node_analysis[("node_analysis")]
        repo_analysis[("repo_analysis")]
        chat_hist[("repo_chat_history")]
    end

    UI --> Router
    Router --> RC & RCC
    RC --> GH & SC & AN & GB & NA
    RCC --> RCS
    NA & GS & RCS --> Ollama & Groq
    GH & SC & AN & GB & NA & RCS --> DB
    Canvas --> Sidebar & Chat
```

### Node Analysis & Chat Pipeline

The following diagram explains how the **node analysis** and **chat feature** work together to enable deep repo-level intelligence:

```mermaid
flowchart TD
    A["🚀 User Imports a GitHub Repository"] --> B["📦 GitHub Service downloads ZIP\n& extracts source files"]
    B --> C["🏷️ Smart Classifier categorizes\neach file (language, category)"]
    C --> D["🔍 Analyzer Service parses\nimports & exports per file"]
    D --> E["💾 All files stored in MongoDB\nwith metadata"]
    E --> F["📊 Graph Builder generates\ndependency graph on demand"]
    E --> G["🤖 Node Analyzer triggered\nin background"]

    G --> H["📐 Topological Sort\n(Kahn's Algorithm)\nLeaf files processed first"]
    
    H --> I["📋 Batch Processing\n5 concurrent files\n0.5s throttle between batches"]

    I --> J{"For Each File"}
    J --> K["📝 Build Rich Prompt:\n• File content (≤6000 chars)\n• Dependency summaries (already analyzed)\n• Files that import this file\n• Graph metrics (depth, in/out degree)"]
    
    K --> L["🧠 LLM Analysis\n(Ollama qwen2.5-coder)"]
    
    L --> M["📊 Structured JSON Output:\n• purpose\n• exports\n• why_connected_to (each import)\n• architectural_role\n• key_patterns\n• concerns\n• summary_for_dependents"]

    M --> N["💾 Save to node_analysis\ncollection in MongoDB"]
    
    N --> O["📡 SSE Event Broadcast\n→ Frontend updates node\nfrom ghosted → solid"]

    O --> P{"All Nodes\nAnalyzed?"}
    P -- "No" --> J
    P -- "Yes" --> Q["🏛️ Repo-Level Synthesis\nAggregates all node summaries"]
    
    Q --> R["💾 Save to repo_analysis\n(layer summaries, data flow,\nentry points, patterns)"]

    R --> S["✅ Repository Fully Analyzed"]

    S --> T{"User Interaction"}
    
    T --> U["💬 File-Level Chat\nUses pre-analyzed node context\n(purpose, role, patterns)\nas conversation grounding"]
    
    T --> V["💬 Repo-Level Chat\nUses repo_analysis synthesis\n(architecture, data flow, patterns)\nas conversation grounding"]
    
    T --> W["💡 Proactive Insights\nAI surfaces 3-5 actionable\nfindings automatically"]

    U --> X["🧠 LLM generates contextual\nanswer about the specific file"]
    V --> Y["🧠 LLM generates contextual\nanswer about the entire repo"]
    W --> Z["🧠 LLM generates warnings,\ntips, and architectural observations"]

    style A fill:#6366f1,color:#fff
    style G fill:#f59e0b,color:#000
    style L fill:#10b981,color:#fff
    style Q fill:#8b5cf6,color:#fff
    style S fill:#22c55e,color:#fff
    style U fill:#3b82f6,color:#fff
    style V fill:#3b82f6,color:#fff
    style W fill:#3b82f6,color:#fff
```

### Repo-Level Synthesis — How Individual Nodes Are Mapped

After every file has been individually analyzed, the system runs `analyze_repo_level()` to **aggregate all node-level summaries** into a single, cohesive repository understanding. Here's exactly how individual nodes map to the repo-level document:

```mermaid
flowchart TD
    Start["✅ All Nodes Analyzed"] --> Fetch["📥 Fetch all node_analysis docs\nwhere status = done"]

    Fetch --> Loop{"For Each\nAnalyzed Node"}

    Loop --> Extract["Extract from each node:\n• file_path\n• architectural_role\n• summary_for_dependents"]

    Extract --> Classify{"Classify by\narchitectural_role"}

    Classify -- "entry_point\ncontroller\nservice" --> Backend["🔧 Backend Layer Bucket"]
    Classify -- "style\ncomponent" --> Frontend["🎨 Frontend Layer Bucket"]
    Classify -- "model" --> Database["🗄️ Database Layer Bucket"]
    Classify -- "config" --> DevOps["⚙️ DevOps Layer Bucket"]
    Classify -- "helper\ntest\nother" --> Other["📦 Other Bucket"]

    Classify -- "role = entry_point" --> EP["🚪 Entry Points List"]

    Backend --> Agg
    Frontend --> Agg
    Database --> Agg
    DevOps --> Agg
    Other --> Agg
    EP --> Agg

    Agg["📋 Build Synthesis Prompt"] --> PromptDetail

    subgraph PromptDetail["Synthesis Prompt Structure"]
        direction TB
        P1["Frontend layer:\nGraphPage.jsx: Main page managing graph state\nCodeNode.jsx: Custom node renderer with badges\nLanguageLegend.jsx: Color legend component\n..."]
        P2["Backend layer:\nmain.py: FastAPI entry point with lifespan\nrepo_controller.py: Import and graph pipeline\ngroq_service.py: LLM calls with retry logic\n..."]
        P3["Database layer:\ndatabase.py: MongoDB connection helpers\nrepository.py: Pydantic schemas\n..."]
        P4["DevOps layer:\nconfig.py: Pydantic settings from env vars\nlogging.conf: Structured logging config\n..."]
        P5["Entry points:\nmain.py, App.jsx, main.jsx"]
    end

    PromptDetail --> LLM["🧠 LLM Synthesis Call\n(Ollama qwen2.5-coder)"]

    LLM --> Output["📊 Structured JSON Output"]

    subgraph Output_Detail["repo_analysis Document"]
        direction TB
        O1["overall_summary\n2-3 paragraph description of what the repo\ndoes and how it is structured"]
        O2["data_flow\nHow data moves from entry to storage"]
        O3["architectural_patterns\ne.g. MVC, REST, Service Layer, Repository Pattern"]
        O4["layer_summaries\nfrontend: paragraph summary\nbackend: paragraph summary\ndatabase: paragraph summary\ndevops: paragraph summary"]
    end

    Output --> Output_Detail

    Output_Detail --> Save["💾 Save to repo_analysis\ncollection in MongoDB"]

    Save --> Status["📡 Set repo status → understood\nSSE stream sends terminal signal"]

    Status --> Ready["🎯 Repo Intelligence Ready\nPowers: repo chat, proactive insights,\nrepo summary endpoint"]

    style Start fill:#22c55e,color:#fff
    style Backend fill:#f97316,color:#fff
    style Frontend fill:#6366f1,color:#fff
    style Database fill:#14b8a6,color:#fff
    style DevOps fill:#8b5cf6,color:#fff
    style Other fill:#6b7280,color:#fff
    style EP fill:#ef4444,color:#fff
    style LLM fill:#10b981,color:#fff
    style Ready fill:#3b82f6,color:#fff
    style Agg fill:#f59e0b,color:#000
```

#### Concrete Example

Imagine a repo with 5 analyzed files. Here's how their `summary_for_dependents` and `architectural_role` get bucketed:

| File | `architectural_role` | `summary_for_dependents` | Mapped To |
|---|---|---|---|
| `main.py` | `entry_point` | "FastAPI app entry point with lifespan startup" | **Backend** + **Entry Points** |
| `repo_controller.py` | `controller` | "Handles import, graph, and explain endpoints" | **Backend** |
| `database.py` | `model` | "MongoDB connection pool and helper functions" | **Database** |
| `GraphCanvas.jsx` | `component` | "React Flow canvas with Dagre layout engine" | **Frontend** |
| `config.py` | `config` | "Pydantic settings loaded from environment vars" | **DevOps** |

These summaries are concatenated per layer (up to 30 backend, 30 frontend, 20 database, 10 devops) and passed to the LLM as a single synthesis prompt. The LLM reads *all* summaries together and produces a cohesive narrative — not a per-file list, but a **connected story** of how the layers interact.

### Why This Architecture Matters

The key insight is that **node-level analysis feeds repo-level intelligence**:

1. **Bottom-Up Analysis** — Leaf files (no dependencies) are analyzed first via topological sort. Each file's one-line `summary_for_dependents` is injected into the prompts of files that import it. This means by the time a high-level controller is analyzed, the LLM already knows what every service it calls actually does.

2. **Pre-Built Context for Chat** — When a user asks "what does this file do?", the system doesn't re-analyze the file from scratch. It retrieves the pre-computed `node_analysis` (purpose, role, patterns, concerns) and injects it as conversation context. This makes chat **faster and more accurate** than raw file-content prompting.

3. **Repo-Level Synthesis** — After all nodes are analyzed, the system aggregates every node summary into a cohesive **repo_analysis** document organized by architectural layer (frontend, backend, database, devops). This becomes the grounding context for repo-level chat, so the AI can answer questions like *"how does data flow from the frontend to the database?"* with precise, file-level detail.

4. **Real-Time Materialization** — The SSE stream broadcasts each completed analysis instantly. The graph transitions from a "ghosted blueprint" to a fully "materialized" architecture as each node lights up, making the analysis process visible and engaging.

### Data Flow

```
User inputs GitHub URL
      │
      ▼
github_service ─────► Download + extract ZIP (80+ extensions)
      │
      ▼
smart_classifier ───► Classify each file (7-tier priority)
      │
      ▼
analyzer_service ───► Parse imports/exports (language-specific parsers)
      │
      ▼
MongoDB ────────────► Store files in `files` collection
      │
      ├──── [on demand] ──► graph_builder ──► Dependency graph → React Flow
      │
      └──── [background] ─► node_analyzer_service
                                │
                                ├── Topological sort (leaves first)
                                ├── Per-file LLM analysis (batches of 5)
                                ├── SSE broadcast → frontend materialization
                                └── Repo-level synthesis
                                        │
                                        ▼
                              User asks a question
                                        │
                                        ▼
                              LLM answers with pre-built context
```

---

## 📁 Folder Structure

```
reposcope-ai/
├── backend/
│   ├── main.py                        # FastAPI app entry point + lifespan startup
│   ├── config.py                      # Pydantic settings (env vars)
│   ├── database.py                    # MongoDB connection helpers
│   ├── requirements.txt               # Python dependencies
│   ├── logging.conf                   # Structured logging configuration
│   ├── .env.example                   # Environment template
│   ├── controllers/
│   │   ├── repo_controller.py         # Repo import, graph, explain, node chat
│   │   └── repo_chat_controller.py    # Repo-level summary, chat, insights
│   ├── services/
│   │   ├── github_service.py          # ZIP download + file extraction from GitHub
│   │   ├── smart_classifier.py        # Multi-priority file language classifier
│   │   ├── classifier_registry.py     # MongoDB-backed classifier rules cache
│   │   ├── classifier_seed.py         # Seeds 80+ classifier rules on first startup
│   │   ├── analyzer_service.py        # Multi-language import/export parser
│   │   ├── graph_builder.py           # Dependency graph + analytics computation
│   │   ├── graph_service.py           # Graph data access helpers
│   │   ├── node_analyzer_service.py   # Background per-node LLM analysis pipeline
│   │   ├── groq_service.py            # LLM service (explain, chat, retry logic)
│   │   ├── repo_chat_service.py       # Repo-level understanding + chat
│   │   ├── sync_service.py            # Incremental repo sync with GitHub
│   │   ├── language_registry.py       # Language color registry (MongoDB)
│   │   ├── llm_import_extractor.py    # Fallback LLM-based import extraction
│   │   ├── bulk_analyzer_service.py   # Batch analysis trigger
│   │   └── ollama_manager.py          # Ollama health checks & model management
│   ├── routes/
│   │   ├── main_router.py             # All API route definitions
│   │   └── analysis_routes.py         # Analysis status + SSE stream sub-router
│   ├── models/
│   │   └── repository.py              # Pydantic request/response schemas
│   └── tests/
│       ├── conftest.py                # Test fixtures
│       ├── test_api.py                # API endpoint tests
│       └── test_classifier.py         # Classifier unit tests
│
├── frontend/
│   ├── index.html                     # HTML entry point
│   ├── package.json                   # Node.js dependencies
│   ├── vite.config.js                 # Vite configuration + API proxy
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   ├── postcss.config.js              # PostCSS config
│   └── src/
│       ├── App.jsx                    # Root component + routing
│       ├── main.jsx                   # React DOM entry point
│       ├── pages/
│       │   └── GraphPage.jsx          # Main page: repo selection, graph, SSE, progress
│       ├── components/
│       │   ├── graph/
│       │   │   ├── GraphCanvas.jsx    # React Flow canvas + Dagre layout engine
│       │   │   ├── CodeNode.jsx       # Custom node: badges, ghost/solid animation
│       │   │   ├── FlowEdge.jsx       # Custom edge: circular highlight, coupling width
│       │   │   ├── FolderGroup.jsx    # Folder boundary rectangles
│       │   │   ├── GraphSearch.jsx    # Fuzzy search + highlight + jump-to
│       │   │   ├── LanguageLegend.jsx # Color legend + custom color picker
│       │   │   └── Graphexportdialog.jsx # Export modal (PNG/SVG/JSON)
│       │   ├── sidebar/
│       │   │   ├── ComponentSidebar.jsx # Node detail: analysis, impact, chat
│       │   │   └── RepoList.jsx       # Left sidebar: repo list + status + progress
│       │   ├── chat/
│       │   │   └── Repochatpanel.jsx  # Floating repo-level Q&A chat panel
│       │   └── ui/
│       │       └── ImportDialog.jsx   # Repo import modal
│       └── lib/
│           └── api.js                 # All API calls (axios)
│
├── screenshots/                       # Feature screenshots for documentation
├── ecosystem.config.cjs               # PM2 process manager configuration
├── DEPLOYMENT.md                      # Detailed deployment guide
└── .gitignore
```

---

## 🔐 Environment Variables

Create `backend/.env` from the provided template:

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONGODB_URI` | ✅ Yes | — | MongoDB Atlas connection string |
| `DB_NAME` | No | `reposcope` | Database name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434/v1` | Ollama API base URL |
| `OLLAMA_ANALYSIS_MODEL` | No | `qwen2.5-coder:7b-instruct` | Model for heavy analysis tasks |
| `OLLAMA_CHAT_MODEL` | No | `qwen2.5-coder:7b-instruct` | Model for user-facing chat |
| `GITHUB_TOKEN` | Recommended | — | GitHub PAT (60 → 5000 req/hr) |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | Allowed CORS origins |
| `GROQ_API_KEY` | No | — | Groq API key (cloud fallback, optional) |
| `GROQ_REPO_ANALYSIS_KEY` | No | — | Separate Groq key for repo analysis (optional) |
| `GROQ_REPO_CHAT_KEY` | No | — | Separate Groq key for chat (optional) |

---

## 📡 API Documentation

Base URL: `http://localhost:8000`

Interactive Swagger docs: `http://localhost:8000/docs`

### Repository Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/import` | Import a GitHub repository |
| `GET` | `/api/v1/repos` | List all imported repositories |
| `DELETE` | `/api/v1/repos/{id}` | Delete a repository and all its data |
| `POST` | `/api/v1/repos/{id}/retry` | Retry a failed import |
| `POST` | `/api/v1/repos/{id}/sync` | Incrementally sync with GitHub |

### Graph & Analysis

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/graph/{id}` | Get dependency graph (nodes + edges + cycles) |
| `POST` | `/api/v1/explain` | Get AI explanation for a file (cached) |
| `POST` | `/api/v1/analysis/{id}/reanalyze` | Force full re-analysis |
| `POST` | `/api/v1/analysis/{id}/node/reanalyze` | Re-analyze a single node |
| `GET` | `/api/v1/analysis/{id}/status` | Get analysis progress |
| `GET` | `/api/v1/analysis/{id}/stream` | SSE stream for real-time progress |

### AI Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/component/chat` | Chat about a specific file |
| `GET` | `/api/v1/repo/{id}/summary` | Get/generate repo-level AI summary |
| `POST` | `/api/v1/repo/{id}/chat` | Chat about the entire repository |
| `GET` | `/api/v1/repo/{id}/chat/history` | Fetch chat history |
| `DELETE` | `/api/v1/repo/{id}/chat/history` | Clear chat history |
| `GET` | `/api/v1/repo/{id}/insights` | Get proactive AI insights |

### Languages

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/languages` | List all languages (optionally filter by `repo_id`) |
| `GET` | `/api/v1/languages/{key}` | Get a specific language entry |
| `PATCH` | `/api/v1/languages/{key}` | Update or reset a language color |

### Example: Import a Repository

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/import \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/expressjs/express", "branch": "master"}'
```

**Response:**
```json
{
  "repo_id": "665a1b2c3d4e5f6a7b8c9d0e",
  "status": "processing",
  "message": "Repository import started"
}
```

### Example: Chat About a File

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/component/chat \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "665a1b2c3d4e5f6a7b8c9d0e",
    "file_path": "src/router/index.js",
    "message": "What middleware does this file use?",
    "history": []
  }'
```

**Response:**
```json
{
  "response": "This file uses three middleware patterns: ..."
}
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
source .venv/bin/activate    # or .venv\Scripts\activate on Windows

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_api.py -v
pytest tests/test_classifier.py -v
```

**Tools used:** pytest, pytest-asyncio, pytest-cov, httpx (test client)

### Frontend Tests

```bash
cd frontend

# Run all tests
npm run test

# Run tests in watch mode
npx vitest --watch
```

**Tools used:** Vitest, @testing-library/react, @testing-library/jest-dom, jsdom

---

## 🚢 Deployment

For detailed deployment instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Quick Start (PM2 — Production)

```bash
# Build the frontend
cd frontend && npm run build && cd ..

# Create logs directory
mkdir -p logs

# Start all services (Ollama + Backend + Frontend)
pm2 start ecosystem.config.cjs

# Check status
pm2 status

# Auto-start on reboot
pm2 save && pm2 startup
```

### Application URLs

| Service | URL |
|---|---|
| Frontend (dev) | http://localhost:5173 |
| Frontend (production) | http://localhost:4173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/v1/health |

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a **Pull Request**

Please ensure:
- Backend tests pass (`pytest`)
- Frontend tests pass (`npm run test`)
- Code follows the existing project style

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](https://github.com/aakash-73/RepoScope-AI/blob/main/LICENSE) file for details.

---

## 👤 Author

**Aakash Reddy**

- GitHub: [@aakash-73](https://github.com/aakash-73)
- LinkedIn: [Aakash Reddy](https://www.linkedin.com/in/aakash-reddy-nuthalapati/)

---

<p align="center">
  <i>Built with ❤️ to make understanding codebases effortless.</i>
</p>
