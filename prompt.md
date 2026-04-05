You are a principal backend architect and staff-level FastAPI engineer.

Your task is to transform the existing KeplerLab-Agentic backend into a production-grade, NotebookLM-like system WITHOUT breaking the rest of the platform.

IMPORTANT:
- Do not act like this is a greenfield project.
- First inspect the existing repository and dependency graph.
- Then produce a migration plan.
- Then implement the refactor incrementally.
- Preserve working non-source features.
- Keep the backend bootable at every major step.
- Do not stop after analysis; actually modify code, add migrations, and add tests.

==================================================
MISSION
==================================================

Replace the current source/data-processing pipeline with a production-grade "source-grounded notebook corpus" architecture inspired by NotebookLM.

The final system must support:
- source upload and ingestion
- source validation and normalization
- extraction/parsing
- long-context storage for small/medium corpora
- chunking + vector indexing for large corpora
- grounded chat with citations
- notebook-scoped retrieval
- downstream reuse by flashcards, quiz, mindmap, presentation, explainer, and podcast/audio workflows
- observability, retries, idempotency, and repair operations
- zero tenant leakage
- backward compatibility for existing routes where possible

==================================================
NON-NEGOTIABLE CONSTRAINTS
==================================================

1. PRESERVE EXISTING PRODUCT SURFACES
Do NOT break or remove these existing feature areas unless absolutely required:
- auth
- notebook management
- chat
- flashcard
- quiz
- mindmap
- ppt / presentation
- explainer
- podcast / audio-related features
- search / proxy
- code execution / artifacts / sandbox
- AI resources
- websocket updates
- model management

2. REPLACE ONLY THE CORE SOURCE PIPELINE
You may replace:
- upload/material ingestion internals
- job queue internals
- RAG retrieval internals
- chunking/embedding/indexing internals
- source persistence contracts
- job states and repair logic

3. BACKWARD COMPATIBILITY
- Existing frontend flows should continue to work.
- If old endpoints exist (upload/materials/jobs), keep compatibility wrappers or aliases.
- If schemas change, provide adapters so current consumers do not break immediately.
- Any breaking DB schema change must be delivered with Prisma migration and migration notes.

4. PRODUCTION GRADE
- Strong typing
- Structured logging
- Retry safety
- Idempotency
- Explicit state machine
- Metrics
- Tests
- Graceful shutdown
- Safe startup recovery
- Tenant isolation at every layer

==================================================
FIRST TASK: REPOSITORY AUDIT
==================================================

Before writing code, inspect the repository and produce a concise architecture map covering:
- all existing routers and which ones depend on source/retrieval outputs
- all services that currently read from material/RAG/job pipeline
- startup/shutdown lifecycle dependencies
- current database models related to notebooks, materials, jobs, citations, outputs
- existing background worker behavior
- current config values relevant to retrieval, embeddings, reranking, sandbox, file handling
- which files can be replaced directly
- which files require compatibility wrappers

Then produce a phased plan:
PHASE 1: compatibility scaffolding
PHASE 2: new source domain + DB models
PHASE 3: new processing pipeline
PHASE 4: retrieval integration
PHASE 5: downstream feature rewiring
PHASE 6: cleanup of legacy code
PHASE 7: tests and production hardening

Do not begin destructive deletion until the dependency map is complete.

==================================================
TARGET ARCHITECTURE
==================================================

Implement a NotebookLM-like architecture with these major domains:

A. SOURCE DOMAIN
Create a first-class Source model and source pipeline that treats every uploaded asset as a durable notebook source.

Each source must support:
- source_id
- user_id
- notebook_id
- source_type
- title
- original_name
- mime_type
- size_bytes
- checksum / fingerprint
- source_uri
- local_file_path
- extraction_status
- indexing_status
- readiness_status
- warning_count
- error_code
- error_message
- retry_count
- created_at
- updated_at
- processed_at

Supported source types:
- FILE
- TEXT
- URL
- YOUTUBE
- NOTE (manual notebook notes as first-class sources)
- AUDIO_TRANSCRIPT (optional if audio uploaded)
- FUTURE types via registry

B. PROCESSOR REGISTRY
Use a strategy/registry pattern:
- BaseSourceProcessor
- FileSourceProcessor
- TextSourceProcessor
- UrlSourceProcessor
- YouTubeSourceProcessor
- NoteSourceProcessor

Each processor must implement:
- validate_input()
- normalize_input()
- extract_content()
- build_source_metadata()
- classify_transient_vs_permanent_error()

Unknown source types must fail with explicit typed errors.

C. NOTEBOOK CORPUS MANAGER
This is the core NotebookLM-like behavior.

Create a notebook-level corpus manager with TWO retrieval lanes:

LANE 1: DIRECT GROUNDING
Use direct or near-direct grounded context for smaller notebook corpora where the total source text is within a configurable threshold.
- Prefer preserving document structure
- Prefer fewer larger sections over aggressive chunking
- Maintain source boundaries and citations
- Useful for source-grounded summarization, note synthesis, cross-document comparison, and study workflows

LANE 2: INDEXED RETRIEVAL
For larger corpora:
- structured chunking
- embeddings
- vector indexing
- lexical retrieval
- reranking
- citation-preserving context assembly

The corpus manager should automatically choose lane 1 or lane 2 based on notebook size, source count, token count, and request type.

D. DERIVED KNOWLEDGE LAYER
Implement notebook-level derived artifacts that can be regenerated from the source corpus:
- notebook summary
- key topics
- FAQ
- study guide
- briefing notes
- timeline / concept map metadata
- follow-up questions
- audio overview script
- source-grounded answer context

These are derived outputs, not primary storage.

==================================================
FOLDER STRUCTURE TO CREATE
==================================================

Create a new domain:

backend/app/services/notebook_corpus/
    __init__.py
    enums.py
    schemas.py
    errors.py
    orchestrator.py
    compatibility.py
    metrics.py
    validators.py
    fingerprints.py
    lifecycle.py

    processors/
        __init__.py
        base.py
        file_processor.py
        text_processor.py
        url_processor.py
        youtube_processor.py
        note_processor.py

    extraction/
        __init__.py
        document_parser.py
        pdf_parser.py
        office_parser.py
        text_parser.py
        media_transcriber.py
        html_parser.py
        normalization.py

    chunking/
        __init__.py
        chunk_models.py
        chunker_factory.py
        structured_chunker.py
        recursive_chunker.py
        section_chunker.py

    storage/
        __init__.py
        source_repository.py
        raw_text_store.py
        citation_store.py
        artifact_store.py

    indexing/
        __init__.py
        embedder.py
        vector_store.py
        lexical_store.py
        index_manager.py

    retrieval/
        __init__.py
        corpus_router.py
        direct_grounding.py
        hybrid_retriever.py
        reranker.py
        citation_context_builder.py
        notebook_context_builder.py

    jobs/
        __init__.py
        states.py
        worker.py
        scheduler.py
        repair.py
        job_repository.py

    outputs/
        __init__.py
        summary_builder.py
        faq_builder.py
        study_guide_builder.py
        key_topics_builder.py
        audio_overview_builder.py

==================================================
NOTEBOOKLM-LIKE WORKFLOW TO IMPLEMENT
==================================================

Implement this end-to-end workflow:

1. ADD SOURCE
- Validate request
- Validate notebook ownership
- Normalize source
- Compute source fingerprint
- Deduplicate by (user_id, notebook_id, fingerprint)
- Save source metadata
- Save uploaded file safely if applicable
- Create job
- Return source_id + job_id + status

2. EXTRACT
- Parse according to source type
- Preserve structure (page numbers, headers, sections, slide numbers, timestamps where possible)
- Normalize text to clean markdown-like format
- Save raw extracted text
- Save extraction metadata
- Mark warnings separately from failures

3. CORPUS BUILD
- Compute notebook corpus totals
- Decide direct-grounding-eligible or indexed
- Build section inventory
- Build chunk inventory if indexing required
- Store stable citation anchors

4. INDEX
- Batch embed in thread pool
- Upsert into vector store with deterministic IDs
- Build lexical search material
- Save index status separately from extraction status

5. READY
- Mark source ready only when extraction is complete
- Mark notebook retrieval-ready when corpus manager confirms enough material is available
- Allow partial readiness: extraction-ready but indexing-pending

6. QUERY
- For notebook chat and other study features, route through notebook corpus manager
- Use direct grounding for small corpora when appropriate
- Use hybrid retrieval for large corpora
- Build grounded context
- Require inline citations in downstream generation

7. DERIVED OUTPUTS
- Flashcards, quiz, mindmap, presentation, explainer, podcast/audio overviews should consume grounded notebook context, not rebuild their own retrieval logic independently

==================================================
DB / PRISMA REQUIREMENTS
==================================================

Inspect current Prisma schema and add or refactor models as needed.

Add or adapt models for:
- Source
- SourceJob
- SourceChunk
- SourceArtifact
- SourceCitationAnchor
- NotebookCorpusState

Requirements:
- no duplicate processing ambiguity
- job state tracking
- source-level and notebook-level readiness
- retry counters
- last error
- warning capture
- fingerprints/checksums
- per-source extraction/index stats

Do NOT remove existing models used by the rest of the product until adapters are in place.
If old models such as Material or BackgroundJob exist, either:
- migrate them into compatibility wrappers, or
- maintain them temporarily while the new source pipeline becomes the system of record

Provide migration scripts and notes.

==================================================
COMPATIBILITY STRATEGY
==================================================

This is critical.

Keep or adapt these route families:
- upload routes
- materials routes
- jobs routes

Implement them as thin compatibility layers over the new notebook corpus orchestrator if necessary.

Also inspect and update these downstream features so they continue to work:
- chat
- flashcard
- quiz
- mindmap
- ppt / presentation
- explainer
- podcast_live
- ai_resource
- notebook pages that list sources/materials/jobs

Do not leave any feature still calling deleted legacy retrieval or legacy processing functions.

==================================================
PROCESSING DETAILS
==================================================

FILE SOURCES
Support at least:
- pdf
- docx
- txt
- md
- pptx
- xlsx/csv if already expected by product
- image-in-pdf OCR where needed
- audio/video transcript if currently expected by product

Requirements:
- MIME validation
- extension validation
- size checks
- path traversal prevention
- atomic file writes
- checksums
- empty file rejection
- encoding handling
- extraction metadata

TEXT SOURCES
- minimum and maximum length checks
- unicode normalization
- whitespace cleanup
- title generation fallback

URL SOURCES
- URL normalization
- block localhost/private IP targets
- timeout and redirect handling
- HTML sanitization
- main-content extraction
- useful metadata like final URL, title, content length
- transient vs permanent fetch errors

YOUTUBE SOURCES
- validate YouTube URL
- extract video id
- use transcript if available
- save timestamp-aware transcript text
- classify “no transcript” as permanent failure unless a fallback is configured

NOTE SOURCES
- notebook notes should become first-class corpus inputs
- editing a note should trigger selective reprocessing, not full notebook reindex

==================================================
RETRIEVAL REQUIREMENTS
==================================================

Build a notebook-level grounded retrieval service.

1. DIRECT GROUNDING MODE
- preserve section structure
- select sections/documents intelligently
- prioritize exact source provenance
- optimize for notebook summarization, comparison, and synthesis

2. HYBRID RETRIEVAL MODE
- dense search
- lexical search
- reciprocal rank fusion
- reranking
- MMR only when actually beneficial
- all filters must include user_id and notebook_id
- stable chunk metadata
- hard cap lexical pool to a safe production limit

3. CITATION MODEL
Every retrieval result must preserve:
- source_id
- chunk_id or section_id
- filename/title
- page or timestamp when available
- section title when available

4. CONTEXT BUILDER
Build final grounded context for LLM usage:
- notebook-scoped
- source-grounded
- token-budget aware
- citation-aware
- suitable for chat, FAQ generation, quiz creation, flashcards, summaries, and presentations

==================================================
CHAT + FEATURE INTEGRATION
==================================================

Refactor existing chat and study features to use ONE shared grounded context builder.

For:
- chat
- flashcard generation
- quiz generation
- mindmap generation
- PPT/presentation generation
- explainer generation
- audio/podcast outline generation

Use:
notebook corpus manager -> grounded retrieval -> citation context builder -> feature-specific prompt

No feature should bypass the notebook corpus and talk to raw source text in its own custom way unless explicitly required.

==================================================
AUDIO OVERVIEW / NOTEBOOKLM-LIKE OUTPUTS
==================================================

Implement NotebookLM-like “audio overview” architecture as a derived output pipeline, not as core ingestion.

Flow:
- grounded notebook context
- outline builder
- two-speaker conversational script builder
- optional TTS generation if audio infra exists
- citations or source map preserved in script metadata
- feature-flagged if incomplete

This pipeline must NOT block normal source ingestion or chat.

==================================================
WORKER / JOB SYSTEM
==================================================

Replace or refactor the worker into a production-safe job runner.

Requirements:
- explicit state machine
- max concurrency from settings
- stuck-job recovery from settings
- heartbeats during long jobs
- retries with capped exponential backoff
- dead-letter state
- selective step retries
- resumable stages
- graceful shutdown
- startup recovery

Stages:
QUEUED
VALIDATING
EXTRACTING
NORMALIZING
CORPUS_BUILDING
INDEXING
READY
FAILED
DEAD_LETTER

Do not keep the old “single material_processing hardcoded path” design.

==================================================
OBSERVABILITY
==================================================

Implement:
- structured logs
- request_id
- job_id
- source_id
- notebook_id
- user_id
- stage timing
- counters by source type and outcome
- queue depth
- stuck job count
- extraction duration
- indexing duration
- retrieval mode chosen (direct vs indexed)
- optional Prometheus endpoint
- safe client-facing errors
- detailed server-side traces

==================================================
RATE LIMITING / SAFETY
==================================================

Protect:
- source add endpoints
- expensive generation endpoints
- retrieval-heavy endpoints

Use configurable limits.
Reject abuse before queueing.
Log rate-limit events.
Preserve tenant isolation in every storage and retrieval path.

==================================================
STARTUP / SHUTDOWN
==================================================

Integrate with existing app lifecycle instead of bypassing it.

The final app startup should:
- connect DB
- initialize corpus services
- warm embedding model safely
- preload reranker safely
- start the new worker
- keep code execution / sandbox startup intact if that feature depends on it
- clean stale temp resources safely
- recover stuck jobs

Shutdown should:
- stop worker gracefully
- flush critical state
- disconnect DB cleanly

==================================================
SETTINGS TO ADD / ADJUST
==================================================

Add safe defaults for:
- JOB_WORKER_POLL_SECONDS
- JOB_MAX_CONCURRENT
- STUCK_JOB_TIMEOUT_MINUTES
- SOURCE_MAX_RETRIES
- SOURCE_RETRY_BACKOFF_BASE_SECONDS
- SOURCE_MAX_FILE_SIZE_MB
- ENABLE_SOURCE_DEDUPLICATION
- DIRECT_GROUNDING_TOKEN_THRESHOLD
- DIRECT_GROUNDING_SOURCE_LIMIT
- DENSE_K
- LEXICAL_POOL
- LEXICAL_K
- RERANK_POOL
- FINAL_K
- EMBED_BATCH_SIZE
- ENABLE_PROMETHEUS
- NOTE_SOURCE_AUTO_REINDEX
- AUDIO_OVERVIEW_ENABLED

Tune retrieval conservatively for production; do not keep overly expensive defaults.

==================================================
LEGACY CLEANUP RULES
==================================================

Do NOT immediately delete legacy files until:
- compatibility adapters exist
- routes still boot
- tests pass
- dependent features are rewired

After migration:
- mark legacy modules deprecated
- remove unreachable imports
- remove dead retrieval code
- remove dead worker code
- keep shims where frontend still depends on old route shapes

==================================================
TESTS
==================================================

Add unit + integration tests for:
- add file/text/url/youtube/note source
- deduplication
- source validation failures
- transient fetch retry
- permanent failure dead-letter
- worker resume
- stuck job recovery
- selective reindex
- selective note reprocess
- tenant isolation
- citation preservation
- direct-grounding mode
- indexed-retrieval mode
- chat grounded answers
- flashcard/quiz/mindmap/presentation consuming shared corpus context
- compatibility wrappers for existing upload/material/job endpoints
- app startup import check

==================================================
FINAL DELIVERABLES
==================================================

After implementation, provide:
1. files changed
2. new architecture diagram in markdown
3. prisma migration summary
4. legacy-to-new mapping table
5. API examples for add source / list sources / get job / retry job / reindex source
6. explanation of direct-grounding vs indexed-retrieval routing
7. list of preserved existing features and how each was rewired
8. test results
9. production readiness checklist
10. follow-up list of optional enhancements

==================================================
ACCEPTANCE CRITERIA
==================================================

Complete only when:
- the backend boots successfully
- existing non-source features still load
- old source-related routes remain compatible or clearly adapted
- new source pipeline is the primary path
- notebook-scoped grounded retrieval works
- citations are preserved
- downstream study features use the shared grounded corpus
- worker is resilient
- retries and dead-letter behavior work
- metrics/logging are production-grade
- no route imports are broken
- no tenant leakage is possible
- tests pass

Start by auditing the existing repository and printing the phased migration plan before making edits.
Then implement phase by phase.
At the end, verify:
python -c "from app.main import app; print('OK')"