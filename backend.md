# KeplerLab Backend Architecture - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Directory Structure](#directory-structure)
4. [Database Schema](#database-schema)
5. [Core Configuration](#core-configuration)
6. [Authentication & Authorization](#authentication--authorization)
7. [API Endpoints](#api-endpoints)
8. [Services Architecture](#services-architecture)
9. [RAG Pipeline](#rag-pipeline)
10. [Agent System](#agent-system)
11. [Background Processing](#background-processing)
12. [WebSocket System](#websocket-system)
13. [Content Generation Services](#content-generation-services)
14. [Code Execution Sandbox](#code-execution-sandbox)
15. [Third-Party Integrations](#third-party-integrations)
16. [Environment Variables](#environment-variables)
17. [Error Handling](#error-handling)
18. [Security Features](#security-features)

---

## Overview

KeplerLab Backend is a FastAPI-based AI-powered learning platform that transforms multi-modal data (documents, videos, URLs, text) into structured knowledge, creative assets, and automated workflows. The backend provides a comprehensive suite of features including:

- **Multi-modal Ingestion**: Upload and process PDFs, videos, URLs, images, and audio files
- **AI Chat**: Context-aware chat with RAG (Retrieval-Augmented Generation)
- **Content Generation**: Flashcards, quizzes, mind maps, presentations, podcasts
- **Code Execution**: Sandboxed Python code execution with chart generation
- **Deep Research**: Web search and research capabilities
- **Explainer Videos**: Generate video explanations from presentations

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL with Prisma ORM |
| **Vector Database** | ChromaDB |
| **LLM Provider** | Ollama / Google Gemini / NVIDIA / Custom API |
| **Embeddings** | BAAI/bge-m3 (Sentence Transformers) |
| **Reranker** | BAAI/bge-reranker-large |
| **Agent Framework** | LangGraph |
| **LLM Abstraction** | LangChain |
| **Audio Transcription** | OpenAI Whisper |
| **OCR** | EasyOCR |
| **TTS** | Edge-TTS |
| **Web Search** | DuckDuckGo |

---

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── core/
│   │   ├── config.py              # Settings and configuration (Pydantic)
│   │   ├── utils.py               # Utility functions
│   │   └── web_search.py          # DuckDuckGo search wrapper
│   ├── db/
│   │   ├── prisma_client.py       # PostgreSQL connection via Prisma
│   │   └── chroma.py               # ChromaDB vector database client
│   ├── models/
│   │   ├── model_schemas.py       # Pydantic models for LLM outputs
│   │   └── shared_enums.py        # Shared enums (DifficultyLevel, IntentOverride)
│   ├── prompts/
│   │   ├── __init__.py            # Prompt composition functions
│   │   ├── chat/                  # Chat-related prompts
│   │   ├── code/                  # Code execution prompts
│   │   ├── generation/            # Content generation prompts
│   │   ├── shared/                # Shared prompt components
│   │   └── system/                # System prompts
│   ├── routes/                    # API route handlers
│   │   ├── auth.py                # Authentication endpoints
│   │   ├── notebook.py            # Notebook CRUD
│   │   ├── upload.py              # File/URL/text upload
│   │   ├── materials.py           # Material management
│   │   ├── chat.py                # Chat (delegates to chat_v2)
│   │   ├── flashcard.py           # Flashcard generation
│   │   ├── quiz.py                # Quiz generation
│   │   ├── mindmap.py             # Mindmap generation
│   │   ├── jobs.py                # Background job status
│   │   ├── ppt.py                 # Legacy presentation
│   │   ├── health.py              # Health checks
│   │   ├── websocket_router.py    # WebSocket for real-time updates
│   │   ├── search.py              # Web search
│   │   ├── proxy.py               # URL proxying for file viewer
│   │   ├── explainer.py           # Explainer video generation
│   │   ├── podcast_live.py        # Podcast generation
│   │   ├── code_execution.py      # Python code execution sandbox
│   │   ├── artifacts.py           # Artifact file serving
│   │   ├── ai_resource.py         # AI resource builder
│   │   ├── models.py              # Model status endpoints
│   │   └── utils.py               # Route utilities
│   └── services/                  # Business logic
│       ├── auth/                  # Authentication service
│       ├── chat_v2/               # Chat orchestration (v2)
│       ├── agent/                 # LangGraph agent orchestrator
│       ├── code_execution/        # Code sandbox
│       ├── explainer/             # Explainer video pipeline
│       ├── flashcard/             # Flashcard generator
│       ├── image_generation/      # Gemini image generation
│       ├── llm_service/           # LLM abstraction layer
│       ├── mindmap/               # Mindmap generator
│       ├── podcast/               # Podcast generation
│       ├── presentation/          # Presentation generation
│       ├── quiz/                  # Quiz generator
│       ├── rag/                   # RAG pipeline
│       ├── research/              # Deep research pipeline
│       ├── text_processing/       # Document extraction & chunking
│       └── tools/                 # Agent tools
├── cli/                           # CLI utilities (reindex, backup, etc.)
├── data/                          # Runtime data storage
│   ├── artifacts/                 # Generated artifacts
│   ├── chroma/                    # Vector database
│   └── exports/                   # Exported files
├── prisma/
│   └── schema.prisma              # Database schema
├── output/                        # Generated outputs
├── requirements.txt
└── .env                           # Environment configuration
```

---

## Database Schema

### Enums

```prisma
enum UserRole { USER, ADMIN }

enum VideoStatus { 
  pending, processing, capturing_slides, 
  generating_script, generating_audio, 
  composing_video, completed, failed 
}

enum ExportStatus { pending, processing, completed, failed }

enum MaterialStatus { 
  pending, processing, ocr_running, 
  transcribing, embedding, completed, failed 
}

enum JobStatus { 
  pending, processing, ocr_running, 
  transcribing, embedding, completed, failed 
}

enum PodcastSessionStatus { 
  created, script_generating, audio_generating, 
  ready, playing, paused, completed, failed 
}
```

### Core Models

#### User
```prisma
model User {
  id            String         @id @default(uuid()) @db.Uuid
  email         String         @unique @db.VarChar(255)
  username      String         @db.VarChar(100)
  hashedPassword String        @map("hashed_password") @db.VarChar(255)
  isActive      Boolean        @default(true) @map("is_active")
  role          UserRole       @default(USER)
  deletedAt     DateTime?      @map("deleted_at")
  createdAt     DateTime       @default(now()) @map("created_at")
  updatedAt     DateTime       @default(now()) @updatedAt @map("updated_at")
  
  // Relations
  notebooks       Notebook[]
  materials       Material[]
  chatSessions    ChatSession[]
  chatMessages    ChatMessage[]
  generatedContent GeneratedContent[]
  refreshTokens   RefreshToken[]
  backgroundJobs  BackgroundJob[]
  // ... more relations
}
```

#### Notebook
```prisma
model Notebook {
  id          String   @id @default(uuid()) @db.Uuid
  userId      String   @map("user_id") @db.Uuid
  name        String   @db.VarChar(255)
  description String?  @db.Text
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @default(now()) @updatedAt @map("updated_at")
  
  owner           User           @relation(fields: [userId], references: [id], onDelete: Cascade)
  materials       Material[]
  chatSessions    ChatSession[]
  chatMessages    ChatMessage[]
  generatedContent GeneratedContent[]
  // ... more relations
}
```

#### Material
```prisma
model Material {
  id           String         @id @default(uuid()) @db.Uuid
  userId       String         @map("user_id") @db.Uuid
  notebookId   String?        @map("notebook_id") @db.Uuid
  filename     String         @db.VarChar(255)
  title        String?        @db.VarChar(510)
  originalText String?        @map("original_text") @db.Text
  status       MaterialStatus @default(pending)
  chunkCount   Int            @default(0) @map("chunk_count")
  sourceType   String?        @default("file") @map("source_type") @db.VarChar(50)
  metadata     Json?
  error        String?        @db.Text
  createdAt    DateTime       @default(now()) @map("created_at")
  updatedAt    DateTime       @default(now()) @updatedAt @map("updated_at")
  
  owner    User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  notebook Notebook? @relation(fields: [notebookId], references: [id], onDelete: SetNull)
  // ... more relations
}
```

#### ChatSession
```prisma
model ChatSession {
  id         String   @id @default(uuid()) @db.Uuid
  notebookId String   @map("notebook_id") @db.Uuid
  userId     String   @map("user_id") @db.Uuid
  title      String   @default("New Chat") @db.VarChar(255)
  createdAt  DateTime @default(now()) @map("created_at")
  updatedAt  DateTime @default(now()) @updatedAt @map("updated_at")
  
  notebook    Notebook      @relation(fields: [notebookId], references: [id], onDelete: Cascade)
  user        User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  chatMessages ChatMessage[]
  artifacts   Artifact[]
}
```

#### ChatMessage
```prisma
model ChatMessage {
  id           String    @id @default(uuid()) @db.Uuid
  notebookId   String    @map("notebook_id") @db.Uuid
  userId       String    @map("user_id") @db.Uuid
  chatSessionId String?  @map("chat_session_id") @db.Uuid
  role         String    @db.VarChar(20)  // 'user' or 'assistant'
  content      String    @db.Text
  agentMeta    String?   @map("agent_meta") @db.Text  // JSON metadata
  createdAt    DateTime  @default(now()) @map("created_at")
  
  notebook    Notebook      @relation(fields: [notebookId], references: [id], onDelete: Cascade)
  user        User          @relation(fields: [userId], references: [id], onDelete: Cascade)
  chatSession ChatSession?  @relation(fields: [chatSessionId], references: [id], onDelete: Cascade)
  responseBlocks ResponseBlock[]
  artifacts   Artifact[]
}
```

#### PodcastSession
```prisma
model PodcastSession {
  id             String               @id @default(uuid()) @db.Uuid
  notebookId     String               @map("notebook_id") @db.Uuid
  userId         String               @map("user_id") @db.Uuid
  mode           String               @default("full") @db.VarChar(20)  // 'full' or 'topic'
  topic          String?              @db.Text
  language       String               @default("en") @db.VarChar(10)
  status         PodcastSessionStatus @default(created)
  currentSegment Int                  @default(0) @map("current_segment")
  hostVoice      String               @default("en-US-GuyNeural") @map("host_voice")
  guestVoice     String               @default("en-US-JennyNeural") @map("guest_voice")
  title          String?              @db.VarChar(255)
  chapters       Json?
  totalDurationMs Int                 @default(0) @map("total_duration_ms")
  summary        String?              @db.Text
  error          String?              @db.Text
  createdAt      DateTime             @default(now()) @map("created_at")
  updatedAt      DateTime             @default(now()) @updatedAt @map("updated_at")
  
  segments    PodcastSegment[]
  doubts      PodcastDoubt[]
  exports     PodcastExport[]
  bookmarks   PodcastBookmark[]
  annotations PodcastAnnotation[]
}
```

#### Artifact
```prisma
model Artifact {
  id            String    @id @default(uuid()) @db.Uuid
  userId        String    @map("user_id") @db.Uuid
  notebookId    String?   @map("notebook_id") @db.Uuid
  sessionId     String?   @map("session_id") @db.Uuid
  messageId     String?   @map("message_id") @db.Uuid
  filename      String    @db.VarChar(255)
  mimeType      String    @map("mime_type") @db.VarChar(128)
  displayType   String?   @map("display_type") @db.VarChar(50)
  sizeBytes     Int       @map("size_bytes")
  downloadToken String    @unique @map("download_token") @db.VarChar(64)
  tokenExpiry   DateTime  @map("token_expiry")
  workspacePath String    @map("workspace_path") @db.Text
  sourceCode    String?   @map("source_code") @db.Text
  createdAt     DateTime  @default(now()) @map("created_at")
}
```

---

## Core Configuration

### Settings (app/core/config.py)

The application uses Pydantic Settings for environment-based configuration:

```python
class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = ""  # Required
    
    # Storage Paths
    CHROMA_DIR: str = "./data/chroma"
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10240  # 10GB default
    
    # JWT Settings
    JWT_SECRET_KEY: str = ""  # Required
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FILE_TOKEN_EXPIRE_MINUTES: int = 5
    
    # Cookie Settings
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_NAME: str = "refresh_token"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # LLM Configuration
    LLM_PROVIDER: str = "OLLAMA"  # OLLAMA, GOOGLE, NVIDIA, MYOPENLM
    OLLAMA_MODEL: str = "llama3"
    GOOGLE_MODEL: str = "models/gemini-2.5-flash"
    NVIDIA_MODEL: str = "qwen/qwen3.5-397b-a17b"
    
    # LLM Temperature Profiles
    LLM_TEMPERATURE_STRUCTURED: float = 0.1  # For JSON output
    LLM_TEMPERATURE_CHAT: float = 0.2        # For chat
    LLM_TEMPERATURE_CREATIVE: float = 0.7    # For creative tasks
    LLM_TEMPERATURE_CODE: float = 0.1        # For code generation
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"
    
    # RAG Configuration
    INITIAL_VECTOR_K: int = 10
    MMR_K: int = 8
    FINAL_K: int = 10
    MAX_CONTEXT_TOKENS: int = 6000
    MIN_SIMILARITY_SCORE: float = 0.3
    
    # Timeouts
    OCR_TIMEOUT_SECONDS: int = 300
    WHISPER_TIMEOUT_SECONDS: int = 600
    LIBREOFFICE_TIMEOUT_SECONDS: int = 120
```

---

## Authentication & Authorization

### JWT-Based Authentication Flow

1. **Login** (`POST /auth/login`)
   - User provides email and password
   - Password verified against bcrypt hash
   - Short-lived access token (15 min) returned in response
   - Long-lived refresh token (7 days) set as HTTP-only cookie

2. **Token Refresh** (`POST /auth/refresh`)
   - Called automatically before access token expiry
   - Validates refresh token from cookie
   - Generates new access token
   - Implements token rotation (old token invalidated)

3. **Token Types**:
   - `access`: For API authentication (15 min expiry)
   - `refresh`: For token renewal (7 days expiry, HTTP-only cookie)
   - `file`: For artifact downloads (5 min expiry)

### Security Features

```python
# Password Hashing
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token Family Tracking (detects token reuse attacks)
model RefreshToken {
  id        String   @id
  userId    String
  tokenHash String   @unique  # SHA-256 hash of token
  family    String            # Token family identifier
  used      Boolean @default(false)
  expiresAt DateTime
}
```

### Token Rotation Flow
```
1. User logs in → access_token + refresh_token (family: ABC)
2. Before expiry → refresh endpoint called
3. New refresh_token issued (same family: ABC)
4. Old token marked as used
5. If old token reused → family compromised → revoke all tokens in family
```

---

## API Endpoints

### Authentication (`/auth`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/auth/signup` | `signup()` | Create new user account |
| POST | `/auth/login` | `login()` | Authenticate and get tokens |
| POST | `/auth/refresh` | `refresh_token_endpoint()` | Rotate refresh token |
| GET | `/auth/me` | `get_me()` | Get current user profile |
| POST | `/auth/logout` | `logout()` | Revoke all user tokens |

### Notebooks (`/notebooks`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/notebooks` | `list_notebooks()` | List user's notebooks |
| POST | `/notebooks` | `create_notebook_endpoint()` | Create new notebook |
| GET | `/notebooks/{id}` | `get_notebook_endpoint()` | Get notebook details |
| PUT | `/notebooks/{id}` | `update_notebook_endpoint()` | Update notebook |
| DELETE | `/notebooks/{id}` | `delete_notebook_endpoint()` | Delete notebook |
| POST | `/notebooks/{id}/thumbnail` | `ensure_notebook_thumbnail_endpoint()` | Generate thumbnail |
| POST | `/notebooks/{id}/content` | `save_generated_content()` | Save generated content |
| GET | `/notebooks/{id}/content` | `get_notebook_content_endpoint()` | Get generated content |
| DELETE | `/notebooks/{id}/content/{cid}` | `delete_generated_content()` | Delete content |
| PATCH | `/notebooks/{id}/content/{cid}/rating` | `rate_generated_content()` | Rate content |

### Upload (`/upload`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/upload` | `upload_file()` | Upload single file |
| POST | `/upload/batch` | `upload_batch()` | Upload multiple files |
| POST | `/upload/url` | `upload_url()` | Upload from URL |
| POST | `/upload/text` | `upload_text()` | Upload text content |
| GET | `/upload/supported-formats` | `get_supported_formats()` | List supported formats |

### Materials (`/materials`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/materials` | `list_materials()` | List user's materials |
| PATCH | `/materials/{id}` | `patch_material()` | Update material |
| DELETE | `/materials/{id}` | `remove_material()` | Delete material |
| GET | `/materials/{id}/text` | `get_material_text_endpoint()` | Get material text |

### Chat (`/chat`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/chat` | `chat_endpoint()` | Stream chat response (SSE) |
| POST | `/chat/block-followup` | `block_followup()` | Follow-up on paragraph block |
| POST | `/chat/optimize-prompts` | `optimize_prompts_endpoint()` | Optimize user prompt |
| POST | `/chat/suggestions` | `suggestions_endpoint()` | Get autocomplete suggestions |
| POST | `/chat/empty-suggestions` | `empty_suggestions_endpoint()` | Get empty state suggestions |
| GET | `/chat/history/{notebook_id}` | `get_notebook_chat_history()` | Get chat history |
| DELETE | `/chat/history/{notebook_id}` | `clear_notebook_chat()` | Clear chat history |
| GET | `/chat/sessions/{notebook_id}` | `get_chat_sessions_endpoint()` | List chat sessions |
| POST | `/chat/sessions` | `create_chat_session_endpoint()` | Create session |
| DELETE | `/chat/sessions/{id}` | `delete_chat_session_endpoint()` | Delete session |
| DELETE | `/chat/message/{id}` | `delete_chat_message_endpoint()` | Delete message |
| PATCH | `/chat/message/{id}` | `update_chat_message_endpoint()` | Update message |

### Flashcards (`/flashcard`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/flashcard` | `create_flashcards()` | Generate flashcards |
| POST | `/flashcard/suggest` | `suggest_count()` | Suggest card count |

### Quiz (`/quiz`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/quiz` | `create_quiz()` | Generate quiz |
| POST | `/quiz/suggest` | `suggest_count()` | Suggest question count |

### Mindmap (`/mindmap`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/mindmap` | `create_mindmap()` | Generate mindmap |

### Presentations (`/presentation`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/presentation/generate` | `generate_presentation()` | Generate presentation |
| POST | `/presentation/suggest` | `suggest_presentation_slides()` | Suggest slides |
| POST | `/presentation/update` | `update_presentation()` | Update presentation |
| GET | `/presentation/{id}` | `get_presentation()` | Get presentation |
| GET | `/presentation/{id}/html` | `get_presentation_html()` | Get HTML |
| GET | `/presentation/{id}/ppt` | `get_presentation_ppt()` | Get PPTX |
| GET | `/presentation/{id}/download` | `download_presentation()` | Download (pptx/pdf/html) |

### Podcast (`/podcast`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/podcast/session` | `create_session()` | Create podcast session |
| GET | `/podcast/session/{id}` | `get_session()` | Get session |
| GET | `/podcast/sessions/{notebook_id}` | `list_sessions()` | List sessions |
| PATCH | `/podcast/session/{id}` | `update_session()` | Update session |
| DELETE | `/podcast/session/{id}` | `delete_session()` | Delete session |
| POST | `/podcast/session/{id}/start` | `start_generation()` | Start generation |
| GET | `/podcast/session/{id}/segment/{idx}/audio` | `get_segment_audio()` | Get audio segment |
| POST | `/podcast/session/{id}/question` | `ask_question()` | Ask Q&A question |
| POST | `/podcast/session/{id}/bookmark` | `add_bookmark()` | Add bookmark |
| POST | `/podcast/session/{id}/annotation` | `add_annotation()` | Add annotation |
| POST | `/podcast/session/{id}/export` | `trigger_export()` | Export podcast |
| GET | `/podcast/voices` | `get_voices()` | Get available voices |
| GET | `/podcast/languages` | `get_languages()` | Get languages |

### Explainer Videos (`/explainer`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/explainer/check-presentations` | `check_presentations()` | Check existing presentations |
| POST | `/explainer/generate` | `generate_explainer()` | Generate explainer video |
| GET | `/explainer/{id}/status` | `get_explainer_status()` | Get status |
| GET | `/explainer/{id}/video` | `get_explainer_video()` | Get video file |

### Code Execution (`/code-execution`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/code-execution/execute-code` | `execute_code()` | Execute code (SSE stream) |
| POST | `/code-execution/run-generated` | `run_generated_code()` | Run generated code |

### Search (`/search`)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/search/web` | `search_web()` | Web search |

### WebSocket (`/ws`)

| Endpoint | Handler | Description |
|----------|---------|-------------|
| `/ws/jobs/{user_id}` | `ws_jobs()` | Real-time job updates |

---

## Services Architecture

### LLM Service (`app/services/llm_service/`)

Provides abstraction over multiple LLM providers:

```python
# Provider Selection
def get_llm(temperature: Optional[float] = None):
    if LLM_PROVIDER == "OLLAMA":
        return ChatOllama(model=OLLAMA_MODEL)
    elif LLM_PROVIDER == "GOOGLE":
        return ChatGoogleGenerativeAI(model=GOOGLE_MODEL)
    elif LLM_PROVIDER == "NVIDIA":
        return ChatNVIDIA(model=NVIDIA_MODEL)
    elif LLM_PROVIDER == "MYOPENLM":
        return CustomAPI()

# Temperature Profiles
LLM_TEMPERATURE_STRUCTURED = 0.1  # For JSON output
LLM_TEMPERATURE_CHAT = 0.2        # For chat
LLM_TEMPERATURE_CREATIVE = 0.7    # For creative tasks
LLM_TEMPERATURE_CODE = 0.1        # For code generation
```

---

## RAG Pipeline

### Components

1. **Embedder** (`app/services/rag/embedder.py`)
   - Generates embeddings using BAAI/bge-m3
   - Stores chunks in ChromaDB with metadata

2. **Secure Retriever** (`app/services/rag/secure_retriever.py`)
   - Tenant-isolated vector search
   - All queries require user_id
   - Material-level filtering

3. **Reranker** (`app/services/rag/reranker.py`)
   - Cross-encoder re-ranking using BAAI/bge-reranker-large
   - Improves relevance of top-k results

4. **Context Formatter** (`app/services/rag/context_formatter.py`)
   - Formats retrieved chunks with citations
   - `[SOURCE 1]`, `[SOURCE 2]` format

5. **Citation Validator** (`app/services/rag/citation_validator.py`)
   - Verifies citations in AI responses
   - Detects hallucinated references

### Retrieval Pipeline Flow

```
1. User Query
      ↓
2. Vector Similarity Search (tenant-isolated)
   - Top-K: 10 results
   - Metadata filtering by material_ids
      ↓
3. MMR (Maximal Marginal Relevance)
   - Lambda: 0.5
   - Reduces redundancy
      ↓
4. Cross-encoder Reranking
   - Model: bge-reranker-large
   - Final-K: 10 results
      ↓
5. Source Diversity Enforcement
   - Ensures multi-material coverage
      ↓
6. Context Formatting
   - Citation-style formatting
   - Truncation to MAX_CONTEXT_TOKENS
```

---

## Agent System

### LangGraph Pipeline

```
analyse → plan → [direct_response | execute_step ↺ advance_step] → synthesize
                                                              ↓
                                                         reflect (self-healing)
```

### Agent Nodes

1. **analyse**: Classifies intent, detects file generation needs
2. **planner**: Creates multi-step execution plan
3. **execute_step**: Runs selected tool
4. **reflect**: Self-healing decision (continue/retry_with_fix/replan/complete)
5. **advance_step**: Moves to next step
6. **direct_response**: Handles pure chat tasks
7. **synthesize**: Generates final response

### Available Tools

| Tool | Description |
|------|-------------|
| `rag` | RAG retrieval from user materials |
| `web_search` | DuckDuckGo web search |
| `research` | Deep multi-query research |
| `python_auto` | Code generation and execution |

### Tool Execution Flow

```python
async def execute_tool(tool_name, state, memory):
    # 1. Get tool specification
    spec = get_available_tools(has_materials).get(tool_name)
    
    # 2. Enrich query with prior observations
    if state.observations and state.current_step_index > 0:
        query = f"{query}\n\n{state.summary_of_observations()}"
    
    # 3. Execute tool
    async for item in spec.execute_fn(query, user_id, notebook_id, ...):
        yield item
    
    # 4. Process result
    memory.add_observation(tool_result)
```

---

## Background Processing

### Worker (`app/services/worker.py`)

Processes material ingestion in background:

```python
async def job_processor():
    while True:
        # 1. Poll for pending jobs
        jobs = await prisma.backgroundjob.find_many(
            where={"status": "pending"},
            take=5
        )
        
        # 2. Process each job
        for job in jobs:
            await process_job(job)
        
        # 3. Sleep before next poll
        await asyncio.sleep(1)
```

### Processing Pipeline

```
1. Create material record (status: pending)
      ↓
2. Extract text (OCR, transcription, document parsing)
   - PDF: PyMuPDF + pdfplumber + OCR fallback
   - Office: unstructured + python-docx + python-pptx
   - Images: EasyOCR
   - Audio/Video: OpenAI Whisper
      ↓
3. Chunk text into segments
   - Overlap: 150 tokens
   - Min chunk length: 100 tokens
      ↓
4. Generate embeddings
   - Model: BAAI/bge-m3
   - Dimension: 1024
      ↓
5. Store in ChromaDB
   - Tenant-isolated by user_id
   - Metadata: material_id, notebook_id, chunk_index
      ↓
6. Update status (completed/failed)
      ↓
7. Generate AI title (background)
```

### Supported Formats

| Category | Formats |
|----------|---------|
| Documents | PDF, DOCX, DOC, TXT, MD, PPTX, PPT, XLSX, XLS, CSV, RTF, ODT, ODS, ODP, EPUB, EML, MSG |
| Images | JPG, JPEG, PNG, GIF, BMP, TIFF, WebP (with OCR) |
| Audio | MP3, WAV, M4A, AAC, OGG, FLAC (with Whisper transcription) |
| Video | MP4, AVI, MOV, MKV, WebM (with transcription) |
| Web | YouTube URLs, web pages |

---

## WebSocket System

### Connection Manager (`app/services/ws_manager.py`)

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.max_connections_per_user = 10
    
    async def connect(self, user_id: str, websocket: WebSocket):
        # Validate connection limit
        if len(self.active_connections.get(user_id, [])) >= 10:
            await websocket.close(code=4000)
            return
        
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
    
    async def broadcast(self, user_id: str, message: dict):
        for connection in self.active_connections.get(user_id, []):
            await connection.send_json(message)
```

### Event Types

| Event | Description |
|-------|-------------|
| `material_status` | Material processing status update |
| `job_complete` | Background job completion |
| `podcast_progress` | Podcast generation progress |
| `podcast_ready` | Podcast ready for playback |
| `podcast_segment_ready` | Individual segment ready |
| `podcast_answer` | Q&A answer ready |

---

## Content Generation Services

### Flashcard Generator

```python
class FlashcardGenerator:
    def generate(self, material_ids, count, difficulty, topic):
        # 1. Retrieve context from materials
        context = self.retriever.search(material_ids, topic)
        
        # 2. Generate flashcards using LLM
        prompt = FLASHCARD_PROMPT.format(
            context=context,
            count=count,
            difficulty=difficulty
        )
        
        # 3. Parse structured output
        cards = llm.invoke(prompt)
        return FlashcardSet(cards)
```

### Quiz Generator

```python
class QuizGenerator:
    def generate(self, material_ids, count, difficulty):
        # Similar to flashcards but with:
        # - Multiple choice questions
        # - Correct answer marking
        # - Explanations for each option
```

### Mindmap Generator

```python
class MindmapGenerator:
    def generate(self, material_ids, topic):
        # 1. Generate hierarchical structure
        # 2. 4-8 main branches
        # 3. Nested sub-branches
        # 4. Topic focusing
```

### Presentation Generator

```python
class PresentationGenerator:
    async def generate(self, notebook_id, material_ids, title, instruction, theme, max_slides):
        # 1. Intent analysis
        intent = self.analyze_intent(instruction)
        
        # 2. Slide strategy planning
        strategy = self.plan_slides(material_ids, intent)
        
        # 3. HTML generation
        html = self.render_html(strategy, theme)
        
        # 4. PPTX export (optional)
        pptx = self.export_pptx(html)
        
        return Presentation(html_path, ppt_path)
```

### Podcast Generator

```python
class PodcastGenerator:
    async def generate(self, session_id, mode, topic):
        # 1. Script generation
        script = await self.generate_script(material_ids, mode, topic)
        
        # 2. Audio synthesis
        for segment in script.segments:
            audio = await self.tts_service.synthesize(
                text=segment.text,
                voice=segment.speaker  # host or guest
            )
            segment.audio_path = audio.path
        
        # 3. Chapter extraction
        chapters = self.extract_chapters(script)
        
        return PodcastSession(segments, chapters)
```

---

## Code Execution Sandbox

### Security Features

1. **Isolation**: Each execution runs in isolated temp directory
2. **Timeout**: Configurable execution timeout (default 15s)
3. **No Network**: Disabled network access
4. **Resource Limits**: Memory and CPU constraints
5. **Code Validation**: Pre-execution safety checks

### Supported Languages

- Python (primary)
- JavaScript
- TypeScript
- C
- C++
- Java
- Go
- Rust
- Bash

### Execution Flow

```python
async def execute_code(code, language, notebook_id, session_id):
    # 1. Create isolated workspace
    workspace = create_temp_workspace()
    
    # 2. Validate code
    validate_code_safety(code)
    
    # 3. Install dependencies (if needed)
    await ensure_packages(required_packages)
    
    # 4. Execute with timeout
    result = await run_with_timeout(
        code=code,
        language=language,
        timeout=CODE_EXECUTION_TIMEOUT
    )
    
    # 5. Capture outputs
    return ExecutionResult(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        charts=result.charts,  # Base64 encoded
        artifacts=result.files
    )
```

### Auto-Repair Feature

When code fails, the system can:
1. Analyze error message
2. Generate fix suggestions
3. Retry with corrected code
4. Maximum 3 repair attempts

---

## Third-Party Integrations

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **ChromaDB** | Vector storage | `CHROMA_DIR` |
| **Prisma** | ORM for PostgreSQL | `DATABASE_URL` |
| **LangChain** | LLM abstraction | Provider-specific |
| **LangGraph** | Agent orchestration | - |
| **Sentence Transformers** | Embeddings | `EMBEDDING_MODEL` |
| **HuggingFace** | Model hub | Automatic |
| **OpenAI Whisper** | Audio transcription | `WHISPER_TIMEOUT_SECONDS` |
| **EasyOCR** | Image OCR | `OCR_TIMEOUT_SECONDS` |
| **Edge-TTS** | Text-to-speech | Voice IDs |
| **DuckDuckGo** | Web search | - |
| **Gemini** | Image generation | `GOOGLE_API_KEY` |

---

## Environment Variables

### Required Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
JWT_SECRET_KEY=<generated-secret-key>
```

### LLM Configuration

```bash
LLM_PROVIDER=OLLAMA  # or GOOGLE, NVIDIA, MYOPENLM
OLLAMA_MODEL=llama3
GOOGLE_API_KEY=<key>  # If using GOOGLE
NVIDIA_API_KEY=<key>  # If using NVIDIA
```

### Optional Variables

```bash
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-large
MAX_UPLOAD_SIZE_MB=10240
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Error Handling

### Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled %s [request_id=%s]", type(exc).__name__, request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id}
    )
```

### HTTP Exception Handler

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

---

## Security Features

### 1. Tenant Isolation

All database queries are filtered by `user_id`:

```python
# Example: Material retrieval
materials = await prisma.material.find_many(
    where={"userId": user_id, "notebookId": notebook_id}
)
```

### 2. Vector Search Security

```python
def secure_similarity_search_enhanced(user_id, query, material_ids, notebook_id):
    # 1. Validate user owns materials
    for material_id in material_ids:
        material = await prisma.material.find_unique(where={"id": material_id})
        if material.userId != user_id:
            raise PermissionError("Access denied")
    
    # 2. Search with user context
    results = chroma_collection.query(
        query_texts=[query],
        where={"user_id": user_id, "material_id": {"$in": material_ids}}
    )
    
    # 3. Post-validate results
    for result in results:
        if result.metadata["user_id"] != user_id:
            raise SecurityError("Cross-tenant data leakage detected")
```

### 3. Rate Limiting

```python
@middleware
async def rate_limit_middleware(request, call_next):
    # Placeholder - currently passes through
    # TODO: Implement per-user rate limiting
    return await call_next(request)
```

### 4. Trusted Host Middleware

```python
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )
```

---

## Startup Sequence

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Connect to database
    await connect_db()
    
    # 2. Warm up embedding model
    await run_in_executor(warm_up_embeddings)
    
    # 3. Preload reranker model
    await run_in_executor(get_reranker)
    
    # 4. Start background job processor
    job_processor_task = asyncio.create_task(job_processor())
    
    # 5. Ensure sandbox packages installed
    await ensure_packages()
    
    # 6. Clean up stale temp directories
    cleanup_stale_dirs()
    
    # 7. Create output directories
    os.makedirs(OUTPUT_DIRS, exist_ok=True)
    
    # 8. Purge expired refresh tokens
    await cleanup_expired_tokens()
    
    yield  # Application runs here
    
    # Shutdown
    await graceful_shutdown()
    await disconnect_db()
```

---

This completes the comprehensive backend architecture documentation for KeplerLab.
