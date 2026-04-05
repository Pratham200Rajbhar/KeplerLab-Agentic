-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('USER', 'ADMIN');

-- CreateEnum
CREATE TYPE "VideoStatus" AS ENUM ('pending', 'processing', 'capturing_slides', 'generating_script', 'generating_audio', 'composing_video', 'completed', 'failed');

-- CreateEnum
CREATE TYPE "ExportStatus" AS ENUM ('pending', 'processing', 'completed', 'failed');

-- CreateEnum
CREATE TYPE "GeneratedContentType" AS ENUM ('PRESENTATION');

-- CreateEnum
CREATE TYPE "SkillRunStatus" AS ENUM ('pending', 'running', 'completed', 'failed');

-- CreateEnum
CREATE TYPE "MaterialStatus" AS ENUM ('pending', 'validating', 'processing', 'ocr_running', 'transcribing', 'chunking', 'embedding', 'completed', 'failed');

-- CreateEnum
CREATE TYPE "JobStatus" AS ENUM ('pending', 'validating', 'processing', 'ocr_running', 'transcribing', 'chunking', 'embedding', 'completed', 'failed', 'dead_letter');

-- CreateEnum
CREATE TYPE "PodcastSessionStatus" AS ENUM ('created', 'script_generating', 'audio_generating', 'ready', 'playing', 'paused', 'completed', 'failed');

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "username" VARCHAR(100) NOT NULL,
    "hashed_password" VARCHAR(255) NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "role" "UserRole" NOT NULL DEFAULT 'USER',
    "deleted_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notebooks" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notebooks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "materials" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID,
    "filename" VARCHAR(255) NOT NULL,
    "title" VARCHAR(510),
    "original_text" TEXT,
    "status" "MaterialStatus" NOT NULL DEFAULT 'pending',
    "chunk_count" INTEGER NOT NULL DEFAULT 0,
    "source_type" VARCHAR(50) DEFAULT 'file',
    "metadata" JSONB,
    "error" TEXT,
    "source_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "materials_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chat_sessions" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "title" VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "chat_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notebook_source_selections" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "material_ids" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notebook_source_selections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "chat_messages" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "chat_session_id" UUID,
    "role" VARCHAR(20) NOT NULL,
    "content" TEXT NOT NULL,
    "agent_meta" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "chat_messages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "generated_content" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "material_id" UUID,
    "content_type" VARCHAR(50) NOT NULL,
    "title" VARCHAR(255),
    "data" JSONB,
    "html_path" TEXT,
    "ppt_path" TEXT,
    "language" VARCHAR(10),
    "material_ids" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "rating" VARCHAR(10),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "generated_content_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "generated_content_materials" (
    "generated_content_id" UUID NOT NULL,
    "material_id" UUID NOT NULL,

    CONSTRAINT "generated_content_materials_pkey" PRIMARY KEY ("generated_content_id","material_id")
);

-- CreateTable
CREATE TABLE "explainer_videos" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "presentation_id" UUID NOT NULL,
    "ppt_language" VARCHAR(10) NOT NULL,
    "narration_language" VARCHAR(10) NOT NULL,
    "voice_gender" VARCHAR(10) NOT NULL,
    "voice_id" VARCHAR(100) NOT NULL,
    "status" "VideoStatus" NOT NULL DEFAULT 'pending',
    "script" JSONB,
    "audio_files" JSONB,
    "video_url" TEXT,
    "duration" INTEGER,
    "chapters" JSONB,
    "error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),

    CONSTRAINT "explainer_videos_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "refresh_tokens" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "token_hash" VARCHAR(255) NOT NULL,
    "family" VARCHAR(255) NOT NULL,
    "used" BOOLEAN NOT NULL DEFAULT false,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "refresh_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "background_jobs" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "job_type" VARCHAR(50) NOT NULL,
    "status" "JobStatus" NOT NULL DEFAULT 'pending',
    "result" JSONB,
    "error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "background_jobs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_token_usage" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "date" DATE NOT NULL,
    "tokens_used" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_token_usage_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "api_usage_logs" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "endpoint" VARCHAR(255) NOT NULL,
    "material_ids" TEXT[],
    "context_token_count" INTEGER NOT NULL DEFAULT 0,
    "response_token_count" INTEGER NOT NULL DEFAULT 0,
    "model_used" VARCHAR(100) NOT NULL,
    "llm_latency" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "retrieval_latency" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "total_latency" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "api_usage_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_execution_logs" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "intent" VARCHAR(50) NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "tools_used" TEXT[],
    "steps_count" INTEGER NOT NULL DEFAULT 0,
    "tokens_used" INTEGER NOT NULL DEFAULT 0,
    "elapsed_time" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_execution_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "response_blocks" (
    "id" UUID NOT NULL,
    "chat_message_id" UUID NOT NULL,
    "block_index" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "response_blocks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "code_execution_sessions" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "stdout" TEXT,
    "stderr" TEXT,
    "exit_code" INTEGER NOT NULL DEFAULT -1,
    "has_chart" BOOLEAN NOT NULL DEFAULT false,
    "elapsed_time" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "code_execution_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "research_sessions" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "query" TEXT NOT NULL,
    "report" TEXT,
    "sources_count" INTEGER NOT NULL DEFAULT 0,
    "queries_count" INTEGER NOT NULL DEFAULT 0,
    "iterations" INTEGER NOT NULL DEFAULT 1,
    "elapsed_time" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "source_urls" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "research_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_sessions" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "mode" VARCHAR(20) NOT NULL DEFAULT 'full',
    "topic" TEXT,
    "language" VARCHAR(10) NOT NULL DEFAULT 'en',
    "status" "PodcastSessionStatus" NOT NULL DEFAULT 'created',
    "current_segment" INTEGER NOT NULL DEFAULT 0,
    "host_voice" VARCHAR(100) NOT NULL DEFAULT 'en-US-GuyNeural',
    "guest_voice" VARCHAR(100) NOT NULL DEFAULT 'en-US-JennyNeural',
    "title" VARCHAR(255),
    "tags" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "chapters" JSONB,
    "total_duration_ms" INTEGER NOT NULL DEFAULT 0,
    "material_ids" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "summary" TEXT,
    "error" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),

    CONSTRAINT "podcast_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_session_materials" (
    "podcast_session_id" UUID NOT NULL,
    "material_id" UUID NOT NULL,

    CONSTRAINT "podcast_session_materials_pkey" PRIMARY KEY ("podcast_session_id","material_id")
);

-- CreateTable
CREATE TABLE "podcast_segments" (
    "id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "index" INTEGER NOT NULL,
    "speaker" VARCHAR(10) NOT NULL,
    "text" TEXT NOT NULL,
    "audio_url" TEXT,
    "duration_ms" INTEGER NOT NULL DEFAULT 0,
    "chapter" VARCHAR(255),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "podcast_segments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_doubts" (
    "id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "paused_at_segment" INTEGER NOT NULL,
    "question_text" TEXT NOT NULL,
    "question_audio_url" TEXT,
    "answer_text" TEXT,
    "answer_audio_url" TEXT,
    "resolved_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "podcast_doubts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_exports" (
    "id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "format" VARCHAR(10) NOT NULL,
    "file_url" TEXT,
    "status" "ExportStatus" NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "podcast_exports_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_bookmarks" (
    "id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "segment_index" INTEGER NOT NULL,
    "label" VARCHAR(255),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "podcast_bookmarks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "podcast_annotations" (
    "id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "segment_index" INTEGER NOT NULL,
    "note" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "podcast_annotations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "artifacts" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID,
    "session_id" UUID,
    "message_id" UUID,
    "filename" VARCHAR(255) NOT NULL,
    "mime_type" VARCHAR(128) NOT NULL,
    "display_type" VARCHAR(50),
    "size_bytes" INTEGER NOT NULL,
    "download_token" VARCHAR(64) NOT NULL,
    "token_expiry" TIMESTAMP(3) NOT NULL,
    "workspace_path" TEXT NOT NULL,
    "source_code" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "artifacts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "skills" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID,
    "slug" VARCHAR(100) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "markdown" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "is_global" BOOLEAN NOT NULL DEFAULT false,
    "tags" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "skills_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "skill_runs" (
    "id" UUID NOT NULL,
    "skill_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID,
    "status" "SkillRunStatus" NOT NULL DEFAULT 'pending',
    "variables" JSONB,
    "step_logs" JSONB,
    "result" JSONB,
    "artifacts" JSONB,
    "error" TEXT,
    "started_at" TIMESTAMP(3),
    "completed_at" TIMESTAMP(3),
    "elapsed_time" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "skill_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sources" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "notebook_id" UUID,
    "source_type" VARCHAR(50) NOT NULL,
    "status" VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    "title" VARCHAR(510),
    "original_name" VARCHAR(255),
    "mime_type" VARCHAR(128),
    "size_bytes" INTEGER,
    "checksum" VARCHAR(128),
    "fingerprint" VARCHAR(128),
    "input_text" TEXT,
    "input_url" TEXT,
    "local_file_path" TEXT,
    "extracted_text" TEXT,
    "extracted_metadata" JSONB,
    "normalized_metadata" JSONB,
    "token_count" INTEGER NOT NULL DEFAULT 0,
    "extraction_status" VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    "indexing_status" VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    "readiness_status" VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    "warning_count" INTEGER NOT NULL DEFAULT 0,
    "warning_messages" JSONB,
    "error_code" VARCHAR(100),
    "error_message" TEXT,
    "retry_count" INTEGER NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "processed_at" TIMESTAMP(3),

    CONSTRAINT "sources_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "source_jobs" (
    "id" UUID NOT NULL,
    "source_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "stage" VARCHAR(30) NOT NULL DEFAULT 'QUEUED',
    "status" VARCHAR(30) NOT NULL DEFAULT 'pending',
    "retry_count" INTEGER NOT NULL DEFAULT 0,
    "last_error" TEXT,
    "metadata" JSONB,
    "heartbeat_at" TIMESTAMP(3),
    "started_at" TIMESTAMP(3),
    "completed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "source_jobs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "source_chunks" (
    "id" UUID NOT NULL,
    "source_id" UUID NOT NULL,
    "chunk_index" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "token_count" INTEGER NOT NULL DEFAULT 0,
    "section_title" VARCHAR(510),
    "page_number" INTEGER,
    "metadata" JSONB,
    "chroma_id" VARCHAR(128),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "source_chunks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "source_citation_anchors" (
    "id" UUID NOT NULL,
    "source_id" UUID NOT NULL,
    "anchor_type" VARCHAR(50) NOT NULL,
    "anchor_label" VARCHAR(510) NOT NULL,
    "page_number" INTEGER,
    "section_title" VARCHAR(510),
    "timestamp" VARCHAR(50),
    "start_offset" INTEGER,
    "end_offset" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "source_citation_anchors_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notebook_corpus_states" (
    "id" UUID NOT NULL,
    "notebook_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "total_tokens" INTEGER NOT NULL DEFAULT 0,
    "source_count" INTEGER NOT NULL DEFAULT 0,
    "ready_count" INTEGER NOT NULL DEFAULT 0,
    "retrieval_mode" VARCHAR(30) NOT NULL DEFAULT 'DIRECT_GROUNDING',
    "corpus_metadata" JSONB,
    "last_rebuilt_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notebook_corpus_states_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "notebooks_user_id_idx" ON "notebooks"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "materials_source_id_key" ON "materials"("source_id");

-- CreateIndex
CREATE INDEX "materials_user_id_idx" ON "materials"("user_id");

-- CreateIndex
CREATE INDEX "materials_notebook_id_idx" ON "materials"("notebook_id");

-- CreateIndex
CREATE INDEX "materials_source_type_idx" ON "materials"("source_type");

-- CreateIndex
CREATE INDEX "chat_sessions_notebook_id_idx" ON "chat_sessions"("notebook_id");

-- CreateIndex
CREATE INDEX "chat_sessions_user_id_idx" ON "chat_sessions"("user_id");

-- CreateIndex
CREATE INDEX "notebook_source_selections_notebook_id_idx" ON "notebook_source_selections"("notebook_id");

-- CreateIndex
CREATE INDEX "notebook_source_selections_user_id_idx" ON "notebook_source_selections"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "notebook_source_selections_notebook_id_user_id_key" ON "notebook_source_selections"("notebook_id", "user_id");

-- CreateIndex
CREATE INDEX "chat_messages_chat_session_id_idx" ON "chat_messages"("chat_session_id");

-- CreateIndex
CREATE INDEX "chat_messages_notebook_id_idx" ON "chat_messages"("notebook_id");

-- CreateIndex
CREATE INDEX "chat_messages_notebook_id_created_at_idx" ON "chat_messages"("notebook_id", "created_at");

-- CreateIndex
CREATE INDEX "generated_content_notebook_id_user_id_content_type_idx" ON "generated_content"("notebook_id", "user_id", "content_type");

-- CreateIndex
CREATE INDEX "explainer_videos_user_id_status_idx" ON "explainer_videos"("user_id", "status");

-- CreateIndex
CREATE UNIQUE INDEX "refresh_tokens_token_hash_key" ON "refresh_tokens"("token_hash");

-- CreateIndex
CREATE INDEX "refresh_tokens_user_id_idx" ON "refresh_tokens"("user_id");

-- CreateIndex
CREATE INDEX "refresh_tokens_family_idx" ON "refresh_tokens"("family");

-- CreateIndex
CREATE INDEX "background_jobs_user_id_idx" ON "background_jobs"("user_id");

-- CreateIndex
CREATE INDEX "user_token_usage_user_id_idx" ON "user_token_usage"("user_id");

-- CreateIndex
CREATE INDEX "user_token_usage_date_idx" ON "user_token_usage"("date");

-- CreateIndex
CREATE UNIQUE INDEX "user_token_usage_user_id_date_key" ON "user_token_usage"("user_id", "date");

-- CreateIndex
CREATE INDEX "api_usage_logs_user_id_idx" ON "api_usage_logs"("user_id");

-- CreateIndex
CREATE INDEX "api_usage_logs_endpoint_idx" ON "api_usage_logs"("endpoint");

-- CreateIndex
CREATE INDEX "api_usage_logs_created_at_idx" ON "api_usage_logs"("created_at");

-- CreateIndex
CREATE INDEX "agent_execution_logs_user_id_idx" ON "agent_execution_logs"("user_id");

-- CreateIndex
CREATE INDEX "agent_execution_logs_notebook_id_idx" ON "agent_execution_logs"("notebook_id");

-- CreateIndex
CREATE INDEX "response_blocks_chat_message_id_idx" ON "response_blocks"("chat_message_id");

-- CreateIndex
CREATE INDEX "code_execution_sessions_user_id_idx" ON "code_execution_sessions"("user_id");

-- CreateIndex
CREATE INDEX "code_execution_sessions_notebook_id_idx" ON "code_execution_sessions"("notebook_id");

-- CreateIndex
CREATE INDEX "research_sessions_user_id_idx" ON "research_sessions"("user_id");

-- CreateIndex
CREATE INDEX "research_sessions_notebook_id_idx" ON "research_sessions"("notebook_id");

-- CreateIndex
CREATE INDEX "podcast_sessions_user_id_idx" ON "podcast_sessions"("user_id");

-- CreateIndex
CREATE INDEX "podcast_sessions_notebook_id_idx" ON "podcast_sessions"("notebook_id");

-- CreateIndex
CREATE INDEX "podcast_sessions_user_id_status_idx" ON "podcast_sessions"("user_id", "status");

-- CreateIndex
CREATE INDEX "podcast_segments_session_id_idx" ON "podcast_segments"("session_id");

-- CreateIndex
CREATE UNIQUE INDEX "podcast_segments_session_id_index_key" ON "podcast_segments"("session_id", "index");

-- CreateIndex
CREATE INDEX "podcast_doubts_session_id_idx" ON "podcast_doubts"("session_id");

-- CreateIndex
CREATE INDEX "podcast_exports_session_id_idx" ON "podcast_exports"("session_id");

-- CreateIndex
CREATE INDEX "podcast_bookmarks_session_id_idx" ON "podcast_bookmarks"("session_id");

-- CreateIndex
CREATE INDEX "podcast_annotations_session_id_idx" ON "podcast_annotations"("session_id");

-- CreateIndex
CREATE UNIQUE INDEX "artifacts_download_token_key" ON "artifacts"("download_token");

-- CreateIndex
CREATE INDEX "artifacts_user_id_idx" ON "artifacts"("user_id");

-- CreateIndex
CREATE INDEX "artifacts_notebook_id_idx" ON "artifacts"("notebook_id");

-- CreateIndex
CREATE INDEX "artifacts_session_id_idx" ON "artifacts"("session_id");

-- CreateIndex
CREATE INDEX "artifacts_download_token_idx" ON "artifacts"("download_token");

-- CreateIndex
CREATE INDEX "skills_user_id_idx" ON "skills"("user_id");

-- CreateIndex
CREATE INDEX "skills_notebook_id_idx" ON "skills"("notebook_id");

-- CreateIndex
CREATE INDEX "skills_slug_idx" ON "skills"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "skills_user_id_notebook_id_slug_key" ON "skills"("user_id", "notebook_id", "slug");

-- CreateIndex
CREATE INDEX "skill_runs_skill_id_idx" ON "skill_runs"("skill_id");

-- CreateIndex
CREATE INDEX "skill_runs_user_id_idx" ON "skill_runs"("user_id");

-- CreateIndex
CREATE INDEX "sources_user_id_idx" ON "sources"("user_id");

-- CreateIndex
CREATE INDEX "sources_notebook_id_idx" ON "sources"("notebook_id");

-- CreateIndex
CREATE INDEX "sources_checksum_idx" ON "sources"("checksum");

-- CreateIndex
CREATE INDEX "sources_fingerprint_idx" ON "sources"("fingerprint");

-- CreateIndex
CREATE INDEX "sources_status_idx" ON "sources"("status");

-- CreateIndex
CREATE UNIQUE INDEX "source_jobs_source_id_key" ON "source_jobs"("source_id");

-- CreateIndex
CREATE INDEX "source_jobs_user_id_idx" ON "source_jobs"("user_id");

-- CreateIndex
CREATE INDEX "source_jobs_stage_idx" ON "source_jobs"("stage");

-- CreateIndex
CREATE INDEX "source_jobs_status_idx" ON "source_jobs"("status");

-- CreateIndex
CREATE INDEX "source_chunks_source_id_idx" ON "source_chunks"("source_id");

-- CreateIndex
CREATE UNIQUE INDEX "source_chunks_source_id_chunk_index_key" ON "source_chunks"("source_id", "chunk_index");

-- CreateIndex
CREATE INDEX "source_citation_anchors_source_id_idx" ON "source_citation_anchors"("source_id");

-- CreateIndex
CREATE UNIQUE INDEX "notebook_corpus_states_notebook_id_key" ON "notebook_corpus_states"("notebook_id");

-- CreateIndex
CREATE INDEX "notebook_corpus_states_notebook_id_idx" ON "notebook_corpus_states"("notebook_id");

-- CreateIndex
CREATE INDEX "notebook_corpus_states_user_id_idx" ON "notebook_corpus_states"("user_id");

-- AddForeignKey
ALTER TABLE "notebooks" ADD CONSTRAINT "notebooks_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "materials" ADD CONSTRAINT "materials_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "materials" ADD CONSTRAINT "materials_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "materials" ADD CONSTRAINT "materials_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "sources"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_sessions" ADD CONSTRAINT "chat_sessions_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_sessions" ADD CONSTRAINT "chat_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notebook_source_selections" ADD CONSTRAINT "notebook_source_selections_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notebook_source_selections" ADD CONSTRAINT "notebook_source_selections_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "chat_messages" ADD CONSTRAINT "chat_messages_chat_session_id_fkey" FOREIGN KEY ("chat_session_id") REFERENCES "chat_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_content" ADD CONSTRAINT "generated_content_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_content" ADD CONSTRAINT "generated_content_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_content" ADD CONSTRAINT "generated_content_material_id_fkey" FOREIGN KEY ("material_id") REFERENCES "materials"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_content_materials" ADD CONSTRAINT "generated_content_materials_generated_content_id_fkey" FOREIGN KEY ("generated_content_id") REFERENCES "generated_content"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_content_materials" ADD CONSTRAINT "generated_content_materials_material_id_fkey" FOREIGN KEY ("material_id") REFERENCES "materials"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "explainer_videos" ADD CONSTRAINT "explainer_videos_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "explainer_videos" ADD CONSTRAINT "explainer_videos_presentation_id_fkey" FOREIGN KEY ("presentation_id") REFERENCES "generated_content"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "refresh_tokens" ADD CONSTRAINT "refresh_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "background_jobs" ADD CONSTRAINT "background_jobs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_token_usage" ADD CONSTRAINT "user_token_usage_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "api_usage_logs" ADD CONSTRAINT "api_usage_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_execution_logs" ADD CONSTRAINT "agent_execution_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "agent_execution_logs" ADD CONSTRAINT "agent_execution_logs_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "response_blocks" ADD CONSTRAINT "response_blocks_chat_message_id_fkey" FOREIGN KEY ("chat_message_id") REFERENCES "chat_messages"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "code_execution_sessions" ADD CONSTRAINT "code_execution_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "code_execution_sessions" ADD CONSTRAINT "code_execution_sessions_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "research_sessions" ADD CONSTRAINT "research_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "research_sessions" ADD CONSTRAINT "research_sessions_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_sessions" ADD CONSTRAINT "podcast_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_sessions" ADD CONSTRAINT "podcast_sessions_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_session_materials" ADD CONSTRAINT "podcast_session_materials_podcast_session_id_fkey" FOREIGN KEY ("podcast_session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_session_materials" ADD CONSTRAINT "podcast_session_materials_material_id_fkey" FOREIGN KEY ("material_id") REFERENCES "materials"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_segments" ADD CONSTRAINT "podcast_segments_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_doubts" ADD CONSTRAINT "podcast_doubts_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_exports" ADD CONSTRAINT "podcast_exports_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_bookmarks" ADD CONSTRAINT "podcast_bookmarks_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "podcast_annotations" ADD CONSTRAINT "podcast_annotations_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "podcast_sessions"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "chat_sessions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "artifacts" ADD CONSTRAINT "artifacts_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "chat_messages"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "skills" ADD CONSTRAINT "skills_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "skills" ADD CONSTRAINT "skills_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "skill_runs" ADD CONSTRAINT "skill_runs_skill_id_fkey" FOREIGN KEY ("skill_id") REFERENCES "skills"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "skill_runs" ADD CONSTRAINT "skill_runs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "skill_runs" ADD CONSTRAINT "skill_runs_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sources" ADD CONSTRAINT "sources_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sources" ADD CONSTRAINT "sources_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "source_jobs" ADD CONSTRAINT "source_jobs_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "sources"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "source_chunks" ADD CONSTRAINT "source_chunks_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "sources"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "source_citation_anchors" ADD CONSTRAINT "source_citation_anchors_source_id_fkey" FOREIGN KEY ("source_id") REFERENCES "sources"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notebook_corpus_states" ADD CONSTRAINT "notebook_corpus_states_notebook_id_fkey" FOREIGN KEY ("notebook_id") REFERENCES "notebooks"("id") ON DELETE CASCADE ON UPDATE CASCADE;
