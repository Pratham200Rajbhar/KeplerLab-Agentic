# AI Learning Studio - Product Requirements Document

## 1. Document Info
- Product: AI Learning Studio
- Program: KeplerLab
- Date: 2026-03-29
- Status: Draft for engineering kickoff
- Owners: Product, Backend, Frontend, AI Platform

## 2. Product Summary
AI Learning Studio is a goal-driven learning system inside KeplerLab where users create a learning plan, complete structured daily sessions, and track progress over time.

This is a standalone learning experience and must remain separate from:
- Notebook chat workflows
- RAG-based material learning
- User-uploaded source dependencies

Core flow:
1. Create learning plan
2. Execute one day at a time
3. Track progress, streak, and mastery

## 3. Problem Statement
Current experiences in KeplerLab are mostly tool-oriented (chat, notebooks, generation utilities). Users who want a guided curriculum and daily progression do not have a dedicated path-based learning product.

Users need:
- A clear day-by-day structure
- Locked progression to build learning habits
- Interactive sessions, not only passive reading
- Progress and mastery visibility

## 4. Goals
- Launch a fully functional AI Learning Studio dashboard as a distinct product area.
- Support end-to-end learning path lifecycle: create, run, track, complete.
- Deliver adaptive daily sessions that react to user performance.
- Enforce sequential progression with unlock rules.
- Provide measurable outcomes (completion, streak, accuracy, retention).

## 5. Non-Goals (Phase 1)
- No RAG retrieval from user documents.
- No dependency on notebook materials.
- No marketplace/community sharing of paths.
- No multi-user classroom features.
- No mobile-native app work (web responsive only).

## 6. User Personas
- Beginner learner: wants a clear plan and simple explanations.
- Career switcher: wants practical project-driven progression.
- Consistent learner: wants daily routine, streaks, and measurable growth.

## 7. User Stories
- As a user, I can create a learning plan with topic, duration, level, and goal type.
- As a user, I can see all days in my path, with locked/unlocked/completed states.
- As a user, I can open the current day and run a guided session.
- As a user, I can complete quiz and game checkpoints before finishing the day.
- As a user, I can see current progress, streak, and weak areas.
- As a user, I can review weak topics in a dedicated review mode.
- As a user, I can complete a final project day at the end of the path.

## 8. Functional Requirements

### 8.1 Path Creation
- FR-001: System must allow creating a path with topic, duration_days, level, and goal_type.
- FR-002: Duration must be validated within configured limits (default 7-90 days).
- FR-003: Path creation must generate day skeletons in persistent storage.
- FR-004: Day 1 must be unlocked at creation time; remaining days locked.

### 8.2 Curriculum Generation
- FR-005: System must generate a day-by-day curriculum sequence (title, objective, difficulty progression).
- FR-006: Last day must default to capstone project format.
- FR-007: Curriculum generation failures must not create partial inconsistent paths.

### 8.3 Daily Learning Session
- FR-008: Day session must contain the following ordered stages:
  - Lesson
  - Interaction
  - Task
  - Quiz
  - Game
  - Completion
- FR-009: Session content should be generated lazily when day is opened.
- FR-010: Generated day payload must be cached and persisted to avoid regeneration on refresh.

### 8.4 Interactive Learning Engine
- FR-011: Engine must enforce stage order using a finite-state transition model.
- FR-012: Wrong answers should trigger explanation plus retry path.
- FR-013: Correct completion should advance stage and eventually mark day complete.
- FR-014: Completing day N unlocks day N+1.

### 8.5 Progress and Analytics
- FR-015: Track completion_percentage at path level.
- FR-016: Track current_day index per path.
- FR-017: Track streak based on day-level activity and completion cadence.
- FR-018: Track quiz_accuracy and weak_topics for adaptive behavior.

### 8.6 Adaptive Learning
- FR-019: System must detect weak concepts from quiz and interaction errors.
- FR-020: Next session content must include additional support for weak concepts.
- FR-021: Strong performance may reduce repetition and increase challenge level.

### 8.7 Review Mode
- FR-022: Users can enter review mode for weak topics without affecting lock progression.
- FR-023: Review mode must provide focused mini-lessons and checks.

### 8.8 Final Project Day
- FR-024: Final day must produce project brief, milestones, and rubric.
- FR-025: Completion must include project submission summary and score rubric output.

## 9. Non-Functional Requirements
- NFR-001: P95 API response for read endpoints < 500 ms (excluding LLM generation calls).
- NFR-002: Day generation endpoint should stream or return within configured timeout with graceful fallback.
- NFR-003: Learning data must be user-isolated by auth ownership checks.
- NFR-004: All mutating endpoints must be idempotent-safe against accidental retries.
- NFR-005: Product must be responsive across desktop and mobile web.
- NFR-006: Feature must include structured logs and metrics for each critical action.

## 10. UX Requirements
- AI Learning Studio appears as a first-class item in main navigation.
- Dashboard layout:
  - Left panel: day list with state icons
  - Main panel: active session stage content
  - Top bar: progress, streak, current day
- Visual states required:
  - Available
  - Locked
  - Completed
  - In progress
- Empty states:
  - No path created
  - Path completed
  - Generation failed with retry

## 11. API Requirements (High-Level)
- Create path
- List paths
- Get path details
- Open day
- Submit interaction answer
- Submit quiz answer(s)
- Submit game action
- Complete day
- Get progress
- Get review recommendations

Detailed contracts are specified in api_spec.md.

## 12. Data Requirements (High-Level)
Required entities:
- LearningPath
- LearningDay
- LearningSessionState
- LearningProgress
- LearningAttempt
- WeakTopicProfile

Detailed schema is specified in database_design.md.

## 13. Success Metrics
Primary:
- Path creation conversion rate
- Day 1 completion rate
- Day-to-day retention rate
- Full path completion rate

Secondary:
- Average streak length
- Quiz accuracy improvement over time
- Review mode usage rate
- Session completion time

Guardrail:
- Session failure rate
- Path generation failure rate
- API error rate (5xx)

## 14. Release Scope

### MVP Scope
- Path creation
- Locked day progression
- Day session with all stages
- Progress and streak tracking
- Basic adaptive support using weak topics

### Post-MVP Scope
- XP/levels rewards economy
- Rich game variations
- Multi-path recommendations
- Coach persona customization controls

## 15. Acceptance Criteria
- User can create a path and see generated day structure.
- User cannot access locked day out of order.
- User can complete stages and day transitions reliably.
- Progress is persisted across refresh and new login sessions.
- Weak topics are updated when user performs poorly.
- Next day adapts content using weak topic profile.
- Final day capstone is generated and completable.

## 16. Risks
- LLM latency spikes can hurt session flow.
- Overly strict lock logic can frustrate users.
- Adaptive rules may overfit short-term mistakes.
- Day generation quality consistency may vary by topic.

Mitigations are detailed in rollout_and_metrics.md and system_design.md.

## 17. Dependencies
- Backend route and service additions in FastAPI.
- Prisma schema updates and database migration.
- Frontend navigation and new route/page implementation.
- Prompt design and evaluation for curriculum/day generation.
- Analytics event instrumentation.

## 18. Open Questions
- Should users be allowed to edit duration after day 1 completion?
- Should skipped days affect streak or only completion timestamps?
- Should review mode be available before day completion?
- Should quiz pass threshold vary by difficulty level?
- Should capstone day include downloadable artifact output in MVP?
