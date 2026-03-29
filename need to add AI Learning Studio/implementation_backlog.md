# AI Learning Studio - Engineering Backlog (File-Level)

## 1. Backend Changes

### 1.1 Router Registration
- Update: backend/app/main.py
  - Add import for learning router
  - Add app.include_router(learning_router)

### 1.2 New Route Module
- Create: backend/app/routes/learning.py

Tasks:
- Define APIRouter(prefix="/learning", tags=["learning"])
- Add request validation models or import from app/models/learning_schemas.py
- Add endpoints from api_spec.md
- Enforce user ownership checks on every endpoint

### 1.3 New Service Package
- Create package: backend/app/services/learning/

Files:
- __init__.py
- path_service.py
- curriculum_generator.py
- day_generator.py
- learning_engine.py
- progress_tracker.py
- quiz_engine.py
- game_engine.py
- adaptive_engine.py
- review_service.py

### 1.4 New Schemas
- Create: backend/app/models/learning_schemas.py
- Create: backend/app/models/learning_enums.py

Suggested models:
- CreateLearningPathRequest
- LearningPathResponse
- LearningDayResponse
- OpenDayRequest/OpenDayResponse
- SubmitInteractionRequest
- SubmitTaskRequest
- SubmitQuizRequest
- SubmitGameRequest
- CompleteDayResponse
- LearningProgressResponse

### 1.5 Prisma Schema
- Update: backend/prisma/schema.prisma

Tasks:
- Add enums from database_design.md
- Add models from database_design.md
- Add User relation lists
- Run prisma generate

## 2. Frontend Changes

### 2.1 New Route
- Create: frontend/src/app/learning/page.jsx

Tasks:
- Load paths and active state
- Render LearningDashboard container
- Handle auth-dependent data fetch lifecycle

### 2.2 New Feature Components
Create directory:
- frontend/src/components/learning/

Files:
- LearningDashboard.jsx
- ProgressHeader.jsx
- DayListPanel.jsx
- SessionPanel.jsx
- CreatePlanModal.jsx
- ReviewPanel.jsx

Create stage components:
- frontend/src/components/learning/stages/LessonStage.jsx
- frontend/src/components/learning/stages/InteractionStage.jsx
- frontend/src/components/learning/stages/TaskStage.jsx
- frontend/src/components/learning/stages/QuizStage.jsx
- frontend/src/components/learning/stages/GameStage.jsx

### 2.3 API Client
- Create: frontend/src/lib/api/learning.js

Tasks:
- Add typed wrappers for all learning endpoints
- Reuse existing fetch wrapper and auth token pattern

### 2.4 Store
- Create: frontend/src/stores/useLearningStore.js

Tasks:
- Manage paths/days/session/progress state
- Expose async actions for all route operations
- Track loading and error states by action key

### 2.5 Navigation Integration
- Update existing sidebar/main nav component that controls primary sections

Tasks:
- Add AI Learning Studio entry
- Add active state style for /learning route

## 3. Prompt and AI Content Artifacts
- Create: backend/app/prompts/learning/

Files:
- curriculum_prompt.md
- day_generation_prompt.md
- interaction_evaluator_prompt.md
- quiz_generator_prompt.md
- game_generator_prompt.md
- adaptive_reinforcement_prompt.md

## 4. Testing Artifacts

### 4.1 Backend Tests
- Create directory: backend/tests/learning/

Files:
- test_paths_api.py
- test_day_open_api.py
- test_stage_transitions.py
- test_progress_tracker.py
- test_locking_rules.py
- test_adaptive_engine.py

### 4.2 Frontend Tests
- Create directory: frontend/src/components/learning/__tests__/

Files:
- LearningDashboard.test.jsx
- DayListPanel.test.jsx
- SessionPanel.test.jsx
- CreatePlanModal.test.jsx

### 4.3 E2E
- Create/extend E2E suite:
  - learning-create-and-complete-day.spec
  - learning-locked-day.spec

## 5. Execution Priority
1. Prisma + backend path/day API skeleton
2. Day open + lazy generation persistence
3. Stage transition engine + progress tracking
4. Frontend route + path/day UI
5. Adaptive and review mode
6. Test hardening and rollout

## 6. Ready-to-Start Task Tickets
- T-001 Add learning models and migration
- T-002 Implement /learning/paths endpoints
- T-003 Implement /learning/days/{id}/open
- T-004 Implement stage submit endpoints
- T-005 Implement /learning/days/{id}/complete
- T-006 Build frontend /learning dashboard shell
- T-007 Build stage components and submit logic
- T-008 Add progress and streak UI
- T-009 Add adaptive/review endpoints and UI
- T-010 Add tests and launch checklist
