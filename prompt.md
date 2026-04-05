You are a senior backend engineer working on the KeplerLab-Agentic FastAPI project.

Your task is to SAFELY DELETE the entire current data processing pipeline end to end.
Do not delete auth, config, database connections, or frontend routes.
Only remove source ingestion, processing, chunking, embedding, retrieval, and job worker code.

=== REPO STRUCTURE REFERENCE ===
The project is at: backend/app/

=== FILES TO DELETE COMPLETELY ===

Delete these files entirely (remove file from disk and all imports):

1.  backend/app/services/material_service.py
2.  backend/app/services/worker.py
3.  backend/app/services/storage_service.py
4.  backend/app/services/file_validator.py
5.  backend/app/services/job_service.py
6.  backend/app/services/notebook_name_generator.py
7.  backend/app/services/notebook_thumbnail_service.py
8.  backend/app/services/rag/embedder.py
9.  backend/app/services/rag/chunker.py
10. backend/app/services/rag/secure_retriever.py
11. backend/app/services/rag/hybrid_retrieval.py
12. backend/app/services/rag/pipeline.py
13. backend/app/services/rag/context_builder.py
14. backend/app/services/rag/context_formatter.py
15. backend/app/services/rag/citation_validator.py
16. backend/app/services/rag/reranker.py
17. backend/app/services/rag/__init__.py
18. backend/app/services/text_processing/ (entire directory and all files inside)
19. backend/app/routes/upload.py
20. backend/app/routes/materials.py
21. backend/app/routes/jobs.py

=== DIRECTORIES TO DELETE ===

Delete these directories entirely:
- backend/app/services/rag/
- backend/app/services/text_processing/
- backend/output/ (contents only, keep folder)
- backend/logs/ (contents only, keep folder)

=== CLEAN UP IMPORTS IN THESE FILES ===

After deleting files, remove ALL import lines referencing deleted modules from:

1. backend/app/main.py
   - Remove: all router imports for upload, materials, jobs
   - Remove: app.include_router() lines for upload_router, materials_router, jobs_router
   - Remove: lifespan references to warm_up_embeddings, get_reranker, job_processor, ensure_packages
   - Remove: from app.services.worker import job_processor, graceful_shutdown, _SHUTDOWN_TIMEOUT
   - Keep: all other routers (auth, chat, notebook, flashcard, quiz, mindmap, ppt, health, websocket, etc.)
   - Keep: DB connect/disconnect, CORS, middleware, exception handlers

2. backend/app/services/performance_logger.py
   - Keep this file but remove any imports referencing deleted modules

3. backend/app/core/config.py
   - Remove settings that ONLY belong to the old pipeline:
     INITIAL_VECTOR_K, LEXICAL_K, LEXICAL_CANDIDATE_POOL, RERANK_CANDIDATES_K, 
     MMR_K, FINAL_K, MMR_LAMBDA, MAX_CONTEXT_TOKENS, RAG_CONTEXT_MAX_TOKENS, 
     MIN_CHUNK_LENGTH, MIN_CONTEXT_CHUNK_LENGTH, MIN_SIMILARITY_SCORE, CHUNK_OVERLAP_TOKENS,
     USE_RERANKER, RERANKER_MODEL, EMBEDDING_VERSION
   - KEEP: EMBEDDING_MODEL, EMBEDDING_DIMENSION, CHROMA_DIR, MODELS_DIR, UPLOAD_DIR

=== CLEAN UP PRISMA SCHEMA ===

In backend/prisma/schema.prisma, check for models used ONLY by the deleted pipeline:
- If BackgroundJob model exists and is only used by worker.py → mark it as TO_REMOVE with a comment
  (Do not actually delete it yet — note it for migration)
- Keep all other models: User, Notebook, etc.

=== GIT CLEANUP ===

After all deletions, provide these git commands:
  git rm --cached backend/logs.txt
  git rm -r --cached backend/output/
  git rm -r --cached backend/app/services/rag/
  git rm -r --cached backend/app/services/text_processing/
  git add .
  git commit -m "chore: remove old data processing pipeline for NotebookLM-style rebuild"

=== VERIFICATION AFTER DELETION ===

Run this and confirm zero import errors remain:
  cd backend
  python -c "from app.main import app; print('OK')"

Fix any remaining broken import that causes that check to fail.

=== DO NOT DELETE ===
- backend/app/routes/auth.py
- backend/app/routes/chat.py
- backend/app/routes/notebook.py
- backend/app/routes/flashcard.py
- backend/app/routes/quiz.py
- backend/app/routes/mindmap.py
- backend/app/routes/ppt.py
- backend/app/routes/health.py
- backend/app/routes/websocket_router.py
- backend/app/routes/models.py
- backend/app/routes/search.py
- backend/app/routes/proxy.py
- backend/app/routes/explainer.py
- backend/app/routes/podcast_live.py
- backend/app/routes/code_execution.py
- backend/app/routes/artifacts.py
- backend/app/routes/ai_resource.py
- backend/app/services/presentation/
- backend/app/services/agent/
- backend/app/services/auth/
- backend/app/services/chat_v2/
- backend/app/services/llm_service/
- backend/app/services/model_manager.py
- backend/app/services/ws_manager.py
- backend/app/db/
- backend/app/core/
- backend/app/models/
- backend/app/prompts/

Output a final checklist of every file deleted and every import line removed.