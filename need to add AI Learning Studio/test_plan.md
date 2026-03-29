# AI Learning Studio - Test Plan

## 1. Test Objectives
- Verify end-to-end learning flow correctness.
- Prevent progression and lock-state regressions.
- Validate adaptive behavior and progress calculations.
- Ensure feature isolation from notebook/RAG systems.

## 2. Test Scope
In scope:
- Backend learning APIs and service logic
- DB transactions and constraints
- Frontend learning route and interactions
- Cross-device responsive behavior

Out of scope (MVP):
- Load testing at production scale
- Localization testing
- Native mobile testing

## 3. Test Layers

### 3.1 Unit Tests (Backend)
Target modules:
- curriculum_generator
- day_generator
- learning_engine
- progress_tracker
- adaptive_engine

Key checks:
- deterministic stage transition rules
- pass/fail evaluation behavior
- weak-topic update logic
- completion percentage math

### 3.2 Integration Tests (Backend)
Endpoint coverage:
- create/list/get path
- list days
- open day
- submit interaction/task/quiz/game
- complete day
- get progress/review

Must validate:
- auth ownership checks
- lock enforcement
- transaction rollback on failure
- idempotent retry behavior (if enabled)

### 3.3 UI/Component Tests (Frontend)
- create plan form validation
- day list lock icons and disabled behavior
- stage rendering by session.stage
- error and retry rendering

### 3.4 End-to-End Journey Tests
Happy path:
1. Create path
2. Open day 1
3. Complete all stages
4. Complete day
5. Verify day 2 unlock and progress updates

Negative path examples:
- Attempt opening locked day
- Submit wrong quiz answers and verify retry loop
- Force generation error and verify retry UI

## 4. Critical Test Scenarios

### TC-001 Path Creation
- Input valid topic/duration/level/goal_type
- Expect 201 and day 1 unlocked

### TC-002 Invalid Path Creation
- duration out of bounds
- Expect 422/400 with validation detail

### TC-003 Locked Day Access
- Open day N+1 before completing day N
- Expect lock error (403/409)

### TC-004 Stage Order Enforcement
- Try quiz submit when session stage is INTERACTION
- Expect conflict and no state change

### TC-005 Interaction Retry Flow
- Submit low-quality interaction answer
- Expect passed=false and feedback with retry guidance

### TC-006 Quiz Scoring
- Submit mixed answers
- Verify score, pass threshold behavior, and weak topic extraction

### TC-007 Day Completion Unlock
- Complete all stages then call complete
- Verify day status completed and next day unlocked

### TC-008 Progress Accuracy
- Verify completion_percentage = completed_days / total_days * 100
- Verify current_day moves correctly

### TC-009 Streak Calculation
- Simulate daily completions and gap day
- Verify streak increment/reset logic

### TC-010 Adaptive Next Day
- Cause weak topic on day N
- Open day N+1 and verify weak-topic reinforcement appears

### TC-011 Ownership Isolation
- User A requests User B path/day
- Expect not found/forbidden behavior

### TC-012 Frontend Recovery
- Simulate API failure on open day
- Verify retry button and no app crash

## 5. Data and Fixture Strategy
- Use dedicated test users and isolated test DB schema.
- Seed deterministic path/day fixtures for transition tests.
- Provide mock generator outputs for stable tests.

## 6. Tooling Suggestions
- Backend: pytest + async test client + test db fixture
- Frontend: React Testing Library + Jest/Vitest
- E2E: Playwright/Cypress (team standard)

## 7. Performance and Reliability Checks
- P95 read endpoint latency under target for non-generation endpoints.
- Open day generation handles timeout/failure gracefully.
- Repeated submit requests do not corrupt state.

## 8. Regression Suite (Required Before Release)
- Full learning journey happy path
- Lock/unlock and progression checks
- Existing notebook/chat smoke tests to confirm no regressions

## 9. Exit Criteria
- 100% pass on critical scenarios (TC-001 to TC-012)
- No P0/P1 defects
- Known P2/P3 documented with mitigation
- Product and engineering signoff for beta flag enablement

## 10. Post-Release Monitoring Checks
- Error rate on learning endpoints
- Day open failure rate
- Stage submit failure rate
- Path creation to day-1 completion conversion
