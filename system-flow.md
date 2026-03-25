# KeplerLab System Flow

This file provides visual end-to-end flow diagrams for the main runtime paths in the current codebase.

## 1. High-Level Runtime Architecture

```mermaid
flowchart LR
  UI[Next.js Frontend<br/>Sidebar Chat Studio] --> API[FastAPI Backend]

  API --> AUTH[Auth Service<br/>JWT Access + Refresh]
  API --> CHAT[Chat V2 + Agent<br/>SSE Streaming]
  API --> UPLOAD[Upload Routes]
  API --> WORKER[Background Worker]
  API --> CODE[Code Execution Sandbox]
  API --> POD[Podcast Services]
  API --> EXP[Explainer Services]

  AUTH --> PG[(PostgreSQL<br/>Prisma)]
  CHAT --> PG
  UPLOAD --> PG
  WORKER --> PG
  POD --> PG
  EXP --> PG
  CODE --> PG

  CHAT --> CHROMA[(Chroma Vector DB)]
  WORKER --> CHROMA

  UPLOAD --> FS[(Filesystem<br/>uploads/output/artifacts)]
  WORKER --> FS
  CODE --> FS
  POD --> FS
  EXP --> FS

  API <--> WS[WebSocket /ws/jobs/:user_id]
  API --> SSE[SSE /chat + /code-execution]
```

## 2. Upload -> Processing -> Material Ready

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant FE as Frontend Sidebar
  participant API as Upload Route
  participant DB as PostgreSQL
  participant WQ as Job Queue Notify
  participant WK as Worker
  participant TP as Text Processing
  participant ST as Storage Service
  participant V as Chroma
  participant WS as WebSocket

  U->>FE: Upload file/url/text
  FE->>API: POST /upload | /upload/batch | /upload/url | /upload/text
  API->>API: Validate input + security checks
  API->>DB: Create Material(status=pending)
  API->>DB: Create BackgroundJob(status=pending)
  API->>WQ: job_queue.notify()
  API-->>FE: 202 Accepted {material_id, job_id}

  WK->>DB: fetch_next_pending_job() FOR UPDATE SKIP LOCKED
  WK->>DB: Set job status processing
  WK->>TP: Extract text (OCR/transcription/web/youtube/file)
  WK->>ST: Save full extracted text
  WK->>TP: Chunk text
  WK->>V: Embed and store chunks
  WK->>DB: Update Material(status=completed, chunkCount, summary)
  WK->>WS: material_update(completed)
  WS-->>FE: Material status update
  FE->>FE: Refresh list and auto-select completed source
```

## 3. Chat Streaming (Normal/RAG/Web/Research/Agent)

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant FE as ChatPanel/useChat
  participant API as /chat endpoint
  participant OR as Chat Orchestrator
  participant RT as Capability Router
  participant T as Tool Layer
  participant L as LLM
  participant DB as Message Store

  U->>FE: Send prompt
  FE->>API: POST /chat (stream=true)
  API->>API: Ensure/Create ChatSession
  API->>OR: chat_stream(...)
  OR->>RT: route_capability(message, materials, intent_override)

  alt RAG
    OR->>T: rag_tool.execute()
    T-->>OR: ToolResult(context + chunks)
  else WEB_SEARCH
    OR->>T: web_search_tool.execute()
    T-->>OR: ToolResult(web results)
  else WEB_RESEARCH
    OR->>T: research_tool.execute()
    T-->>OR: phase/source/report events
  else CODE_EXECUTION
    OR->>T: python_tool.execute()
    T-->>OR: code/events
  else AGENT
    OR->>T: run_agent() LangGraph pipeline
    T-->>OR: agent_* events + artifacts
  end

  OR->>L: Build prompt + stream response
  loop token stream
    L-->>OR: chunk
    OR-->>FE: SSE token
  end

  OR->>DB: save_user_message
  OR->>DB: save_assistant_message(meta)
  OR->>DB: save_response_blocks
  OR-->>FE: SSE blocks/meta/done
  FE->>FE: Render message, sources, artifacts, progress
```

## 4. Agent LangGraph Internal Flow

```mermaid
flowchart TD
  A[analyse] --> P[planner]
  P -->|empty plan| D[direct_response]
  P -->|has plan| E[execute_step]

  E --> R[reflect]
  R -->|continue| ADV[advance_step]
  ADV --> E
  R -->|retry_with_fix| E
  R -->|replan| ADV
  R -->|complete| S[synthesize]

  E -->|max steps/tool calls| S
  D --> END1([END])
  S --> END2([END])

  subgraph Streaming + Persistence
    Q[asyncio.Queue SSE events]
    SAVE[save user + assistant + blocks + artifact links]
  end

  E --> Q
  R --> Q
  D --> Q
  S --> Q
  S --> SAVE
```

## 5. Code Execution -> Artifact Registration

```mermaid
sequenceDiagram
  autonumber
  participant FE as Frontend
  participant API as /code-execution/execute-code
  participant SEC as Security Validator
  participant SB as Sandbox Runner
  participant LLM as Repair LLM
  participant FS as Artifacts Dir
  participant DB as Artifact Table

  FE->>API: POST code + timeout + notebook/session
  API->>SEC: validate_code + sanitize_code
  alt Unsafe
    API-->>FE: SSE execution_blocked
  else Safe
    API->>SB: run_in_sandbox
    alt Missing approved module
      API->>SB: install on-demand and rerun
    end
    alt Execution failed
      API->>LLM: get code repair suggestion
      API-->>FE: SSE repair_suggestion
    else Execution success
      API->>API: detect output files
      loop each output
        API->>FS: copy to permanent artifacts dir
        API->>DB: create Artifact record
        API-->>FE: SSE artifact
      end
      API-->>FE: SSE execution_done
    end
  end
```

## 6. WebSocket Job/Material Updates

```mermaid
sequenceDiagram
  autonumber
  participant FE as useMaterialUpdates
  participant WS as /ws/jobs/{user_id}
  participant WSM as ws_manager
  participant WK as Worker/Services

  FE->>WS: Connect (token query or auth message)
  WS->>WS: Validate token + user match
  WS->>WSM: connect_user(user_id, websocket)
  WS-->>FE: connected

  loop keepalive
    WS-->>FE: ping
    FE-->>WS: pong
  end

  WK->>WSM: send_to_user(material_update/notebook_update/...)
  WSM-->>FE: JSON event
  FE->>FE: Update sources/notebook title/podcast store
```

## 7. Presentation Async Generation Flow

```mermaid
sequenceDiagram
  autonumber
  participant FE as StudioPanel
  participant API as /presentation/async
  participant JOB as BackgroundJob
  participant GEN as ppt.generator

  FE->>API: POST /presentation/async
  API->>JOB: create_job(type=presentation)
  API-->>FE: {job_id, status: pending}

  API->>GEN: background task _run_ppt_job
  GEN-->>API: presentation JSON/HTML/slides
  API->>JOB: update_job_status(completed | failed)

  loop polling
    FE->>API: GET /jobs/{job_id}
    API-->>FE: processing/completed
  end
```

## 8. Explainer Generation Flow

```mermaid
sequenceDiagram
  autonumber
  participant FE as Explainer UI
  participant API as /explainer/generate
  participant DB as Prisma
  participant PPT as Presentation Generator
  participant BG as Background Task
  participant VID as Video Composer/TTS
  participant FS as Explainer Output

  FE->>API: generate request (materials/lang/voice)
  alt Reuse presentation
    API->>DB: load existing presentation
  else Create new
    API->>PPT: generate_presentation
    API->>DB: save GeneratedContent(presentation)
  end

  API->>DB: create ExplainerVideo(status=pending)
  API->>BG: process_explainer_video(...)
  API-->>FE: explainer_id

  BG->>VID: script + audio + composition
  VID->>FS: write explainer_final.mp4
  BG->>DB: update status completed/failed

  FE->>API: GET /explainer/{id}/status (poll)
  FE->>API: GET /explainer/{id}/video
```

## 9. Podcast Session Flow

```mermaid
sequenceDiagram
  autonumber
  participant FE as PodcastStudio
  participant API as /podcast/* routes
  participant SM as session_manager
  participant QA as qa_service
  participant EX as export_service
  participant TTS as tts_service
  participant DB as Prisma
  participant FS as Podcast Files

  FE->>API: POST /podcast/session
  API->>SM: create session + validate materials
  SM->>DB: create PodcastSession
  API-->>FE: session id

  FE->>API: POST /podcast/session/{id}/start
  API->>SM: start_generation
  SM->>TTS: generate segment audio
  TTS->>FS: audio files
  SM->>DB: segments + status ready/playing

  FE->>API: GET segment/session audio endpoints
  API-->>FE: audio stream

  FE->>API: POST question/bookmark/annotation
  API->>QA: handle question (doubt + answer)
  API->>DB: store doubts/bookmarks/annotations

  FE->>API: POST /export
  API->>EX: create export (pdf/json)
  EX->>FS: write export file
  EX->>DB: export status
```

## 10. Frontend Panel Coordination Flow

```mermaid
flowchart LR
  NB[Notebook Page] --> SB[Sidebar]
  NB --> CP[ChatPanel]
  NB --> ST[StudioPanel]

  SB -->|set materials + selected sources| STORE[(Zustand Stores)]
  CP -->|read selected sources| STORE
  ST -->|read selected sources| STORE

  CP -->|SSE /chat| API[Backend]
  SB -->|Upload/Search/WebSocket| API
  ST -->|Generation APIs| API

  API -->|material_update/notebook_update| SB
  STORE --> NB
```

## 11. Notes

- SSE is the primary transport for long-running chat/agent/code responses.
- WebSocket is used for background status fanout (material and notebook updates, plus podcast events).
- Persistent state lives in PostgreSQL; semantic retrieval state lives in Chroma; binary artifacts live on filesystem with DB metadata references.
