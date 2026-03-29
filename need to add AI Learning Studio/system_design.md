# AI Learning Studio - System Design

## 1. Overview
AI Learning Studio is a standalone subsystem for goal-driven learning paths.

It will run alongside existing notebook/chat/studio features but with strict boundary rules:
- No dependency on notebook materials
- No RAG retrieval
- No user-upload document pipeline

## 2. Existing Architecture Alignment
Current stack observed in repository:
- Backend: FastAPI routers in backend/app/routes, services in backend/app/services
- Persistence: Prisma Python client with schema in backend/prisma/schema.prisma
- Frontend: Next.js app router under frontend/src/app with Zustand stores
- Auth: Existing token-based auth and user ownership checks via get_current_user

AI Learning Studio should follow the same feature pattern used by routes like skills/notebook/quiz:
- Dedicated route module
- Dedicated service package
- Pydantic request/response models
- Prisma models + indexes

## 3. High-Level Architecture

### 3.1 Backend Components (new)
Create new package:
- backend/app/services/learning/path_service.py
- backend/app/services/learning/curriculum_generator.py
- backend/app/services/learning/day_generator.py
- backend/app/services/learning/learning_engine.py
- backend/app/services/learning/progress_tracker.py
- backend/app/services/learning/quiz_engine.py
- backend/app/services/learning/game_engine.py
- backend/app/services/learning/adaptive_engine.py
- backend/app/services/learning/review_service.py

Create new route:
- backend/app/routes/learning.py

Create new model schemas:
- backend/app/models/learning_schemas.py
- backend/app/models/learning_enums.py

### 3.2 Frontend Components (new)
Create new app route:
- frontend/src/app/learning/page.jsx

Create new feature components:
- frontend/src/components/learning/LearningDashboard.jsx
- frontend/src/components/learning/DayListPanel.jsx
- frontend/src/components/learning/SessionPanel.jsx
- frontend/src/components/learning/ProgressHeader.jsx
- frontend/src/components/learning/stages/LessonStage.jsx
- frontend/src/components/learning/stages/InteractionStage.jsx
- frontend/src/components/learning/stages/TaskStage.jsx
- frontend/src/components/learning/stages/QuizStage.jsx
- frontend/src/components/learning/stages/GameStage.jsx
- frontend/src/components/learning/CreatePlanModal.jsx

Create API client module:
- frontend/src/lib/api/learning.js

Create store:
- frontend/src/stores/useLearningStore.js

Integrate navigation item in existing layout/sidebar entry point.

## 4. Domain Model

### 4.1 Core Concepts
- Learning Path: top-level course plan for a user
- Learning Day: one sequential day in a path
- Day Content: lazily generated structured session payload
- Session State: current stage and progress for an open day
- Progress: aggregate metrics per user/path
- Attempt: granular answer/interaction attempts
- Weak Topic Profile: concept-level mastery map for adaptation

### 4.2 State Machine
Day execution state machine:
- LESSON -> INTERACTION -> TASK -> QUIZ -> GAME -> COMPLETE

Valid transitions:
- Only forward transitions by default
- Retry transitions within current state allowed on failed checks
- COMPLETE is terminal for the day

## 5. API Design
Base prefix:
- /learning

Primary endpoints:
- POST /learning/paths
- GET /learning/paths
- GET /learning/paths/{path_id}
- GET /learning/paths/{path_id}/days
- POST /learning/days/{day_id}/open
- POST /learning/days/{day_id}/interaction
- POST /learning/days/{day_id}/task
- POST /learning/days/{day_id}/quiz
- POST /learning/days/{day_id}/game
- POST /learning/days/{day_id}/complete
- GET /learning/paths/{path_id}/progress
- GET /learning/paths/{path_id}/review

Detailed payloads are in api_spec.md.

## 6. Backend Runtime Flow

### 6.1 Path Creation Flow
1. Route validates request payload.
2. path_service creates path with status=active.
3. curriculum_generator returns day skeletons.
4. Persist all days in transaction:
   - day 1 unlocked
   - day 2..N locked
5. progress_tracker initializes row (current_day=1, completion=0).

### 6.2 Day Open Flow (Lazy Generation)
1. Verify ownership and day unlocked.
2. If day content exists, return cached payload.
3. Else:
   - gather adaptation context (weak topics, prior accuracy)
   - day_generator generates structured payload
   - persist payload JSON in day row
4. Initialize/refresh session state to LESSON stage.

### 6.3 Stage Submission Flow
1. Verify day is open and not completed.
2. learning_engine validates current stage and request type.
3. Stage-specific engine evaluates answer:
   - interaction logic
   - quiz scoring
   - game challenge scoring
4. Persist attempt record.
5. If pass threshold met:
   - advance stage
   - emit updated session state
6. If fail:
   - return explanation + retry instructions

### 6.4 Day Completion Flow
1. Ensure all required stages passed.
2. Mark day status=completed.
3. Unlock next day (if exists).
4. progress_tracker recomputes percentage/current_day/streak.
5. adaptive_engine updates weak-topic profile.

## 7. Database Design
Data model additions will be made in backend/prisma/schema.prisma:
- LearningPath
- LearningDay
- LearningProgress
- LearningSessionState
- LearningAttempt
- LearningWeakTopic

See database_design.md for full proposed Prisma schema.

## 8. Concurrency and Consistency
- Use atomic updates for day completion + next-day unlock.
- Use optimistic checks on stage transitions to prevent double-submits.
- Idempotency key support for stage submission endpoints (optional but recommended).
- Ensure one active session state per user/day.

## 9. Caching Strategy
- Day content is generated once and persisted in day payload JSON.
- In-memory cache is optional; DB persistence is source of truth.
- Invalidate/recompute only when explicit regeneration requested.

## 10. Security and Authorization
- All endpoints require authenticated user.
- Every read/write filters by userId ownership.
- Reject cross-user path/day IDs with 404-style response.
- Do not expose internal prompt details in public responses.

## 11. Observability
Log fields for every mutating operation:
- user_id
- path_id
- day_id
- stage
- action
- latency_ms
- status

Metrics:
- learning_path_created_total
- learning_day_open_total
- learning_stage_submit_total
- learning_day_complete_total
- learning_stage_fail_total
- learning_generation_latency_ms

## 12. Failure Handling
- Curriculum/day generation failures return recoverable errors with retry path.
- Partial transaction failures must rollback to consistent prior state.
- Stage submit failures should not advance state.
- Circuit-break fallback for LLM provider unavailability:
  - return temporary unavailability
  - preserve current session state

## 13. Performance Targets
- Non-generation reads: P95 < 500 ms
- Mutating stage submissions: P95 < 700 ms
- Day generation: P95 < 8 s (with progressive loading UI)

## 14. Frontend Integration

### 14.1 Navigation
- Add new first-level navigation entry: AI Learning Studio
- Route target: /learning
- Keep notebook and learning experiences separate

### 14.2 Layout
- Left: day list with lock/available/completed states
- Top: progress and streak
- Main: stage-specific session renderer

### 14.3 State Management
Zustand store responsibilities:
- activePath
- days
- currentDay
- sessionState
- progress
- reviewRecommendations
- loading/error states per operation

## 15. Integration With Existing System
- Register new router in backend/app/main.py using include_router
- Keep learning feature independent of chat/skills services
- Reuse common auth dependency and JSON response conventions
- Reuse frontend API config/auth interceptors in frontend/src/lib/api/config

## 16. Rollout Strategy
- Phase 1: hidden behind backend + frontend feature flag
- Phase 2: internal users and selected beta users
- Phase 3: full release with dashboards and alerting

Detailed rollout and risk controls are in rollout_and_metrics.md.

## 17. Sequence Diagrams (Text)

### 17.1 Create Path
Client -> learning route -> path_service -> curriculum_generator -> prisma txn -> response

### 17.2 Open Day
Client -> learning route -> learning_engine.open_day -> day_generator (if empty) -> persist -> response

### 17.3 Submit Quiz Stage
Client -> learning route -> quiz_engine.evaluate -> attempt persistence -> state transition -> progress update -> response

## 18. Open Technical Decisions
- Whether to stream day generation tokens/events (SSE) or keep synchronous JSON responses in MVP.
- Whether adaptive profile updates should run inline or in background job.
- Whether game engine in MVP is rule-based templates or LLM-generated micro-challenges.
