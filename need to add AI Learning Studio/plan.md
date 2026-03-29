# AI Learning Studio - Implementation Plan

## 1. Objective
Implement AI Learning Studio as a standalone goal-driven learning system in KeplerLab with:
- Plan creation
- Day-by-day locked execution
- Adaptive progression
- Progress tracking

This plan is designed for practical execution against the current codebase.

## 2. Implementation Principles
- Keep learning subsystem isolated from notebook/RAG flow.
- Follow existing FastAPI route/service and Prisma conventions.
- Ship in small, testable increments.
- Preserve backward compatibility for existing APIs and frontend routes.

## 3. Workstreams
- WS-1 Product and UX
- WS-2 Backend APIs and service layer
- WS-3 Data model and migrations
- WS-4 Frontend route, state, and interactions
- WS-5 Prompt/content quality and adaptation logic
- WS-6 Testing and release hardening

## 4. Phased Plan

### Phase 0 - Discovery and Design Lock (2-3 days)
Deliverables:
- Finalized PRD
- Finalized system design
- API contract freeze (v1)
- DB schema freeze (v1)

Tasks:
- Confirm MVP boundaries and non-goals
- Confirm lock/unlock behavior and pass thresholds
- Confirm adaptation strategy for weak topics
- Sign off on endpoint names and payloads

Exit criteria:
- No critical open product/architecture questions

### Phase 1 - Data Layer Foundation (2-3 days)
Deliverables:
- Prisma schema updates
- Migration scripts
- Seed helpers for local development

Tasks:
- Add learning models in backend/prisma/schema.prisma
- Add enums for path/day/session statuses
- Create required indexes and unique constraints
- Generate Prisma client

Exit criteria:
- Local migration succeeds
- CRUD smoke test for new models passes

### Phase 2 - Backend Core APIs (4-6 days)
Deliverables:
- learning route module
- path/day/progress service modules
- basic generation adapters

Tasks:
- Add backend/app/routes/learning.py
- Add backend/app/services/learning package and initial modules
- Implement path CRUD/list/get
- Implement day open endpoint with lazy content generation
- Implement stage submission endpoints and transitions
- Implement day completion and next-day unlock
- Register router in backend/app/main.py

Exit criteria:
- End-to-end API flow passes manual and automated checks
- Auth ownership checks enforced on all endpoints

### Phase 3 - Frontend MVP Experience (4-6 days)
Deliverables:
- New learning route (/learning)
- Dashboard with day list + session panel + progress header
- Create-plan modal and day execution UI

Tasks:
- Add frontend route page
- Add learning API client module
- Add Zustand learning store
- Implement create plan flow
- Implement day open and stage progression UI
- Add navigation entry in main sidebar
- Handle loading/error/empty states

Exit criteria:
- User can complete full flow from create plan to day completion
- UI is responsive on desktop and mobile

### Phase 4 - Adaptive and Review Enhancements (3-4 days)
Deliverables:
- Weak-topic tracking
- Adapted day generation prompts
- Review mode endpoints and UI

Tasks:
- Implement weak-topic profile writes from quiz/interactions
- Feed weak-topic context into day generation
- Add review mode service and panel
- Add metrics for adaptation impact

Exit criteria:
- Demonstrable adaptation in next-day content
- Review mode works independently of lock progression

### Phase 5 - Hardening and Launch (3-4 days)
Deliverables:
- Integration tests and regression coverage
- Observability dashboard events
- Feature flag rollout plan

Tasks:
- Add API tests for lock logic and transitions
- Add UI flow tests for create/open/complete day
- Add performance checks and fallback behavior
- Roll out behind feature flag and monitor

Exit criteria:
- Launch readiness checklist signed off

## 5. Sprint-Friendly Backlog

### Backend
- B-01 Add learning enums and models
- B-02 Create path service + curriculum generator
- B-03 Implement day generator and payload persistence
- B-04 Implement learning engine state transitions
- B-05 Implement progress tracker updates
- B-06 Add review/adaptive service hooks
- B-07 Add route handlers + validation models
- B-08 Add logging, metrics, and error mapping

### Frontend
- F-01 Add learning navigation entry
- F-02 Build create plan modal/form
- F-03 Build day list panel with lock states
- F-04 Build session panel with stage renderer
- F-05 Add quiz and game interaction components
- F-06 Build progress header and streak widget
- F-07 Add review mode panel
- F-08 Add loading/error/empty states and skeletons

### QA and DevOps
- Q-01 API contract tests
- Q-02 State transition tests
- Q-03 Frontend journey tests
- Q-04 Performance baseline checks
- Q-05 Rollout monitoring and alert thresholds

## 6. Dependencies
- LLM prompt definitions for curriculum/day generation
- Prisma migration approval and deployment window
- Product signoff on scoring thresholds
- UX signoff on stage interactions and copy

## 7. Risks and Mitigations
- Risk: LLM generation latency too high
  - Mitigation: lazy generation + cached payload + retry/fallback
- Risk: lock logic bugs cause blocked progression
  - Mitigation: strong transition tests + transactional updates
- Risk: inconsistent adaptive behavior
  - Mitigation: deterministic weak-topic scoring rubric
- Risk: regression in notebook UX from nav changes
  - Mitigation: isolated route and smoke tests

## 8. Milestones
- M1 Design lock complete
- M2 Data and backend MVP complete
- M3 Frontend MVP complete
- M4 Adaptive/review complete
- M5 Launch-ready

## 9. Definition of Done
- All MVP requirements implemented and test-covered
- Feature behind controllable flag
- Observability for critical flows enabled
- No P0/P1 open defects
- Stakeholder signoff complete

## 10. Recommended Delivery Order (Fastest Path)
1. Path create/list/get + DB schema
2. Day open + lazy generation persistence
3. Stage transition engine
4. Day complete + unlock + progress
5. Frontend page + day list + session panel
6. Adaptive/review enhancements
7. Hardening and rollout
